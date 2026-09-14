from odoo import api, fields, models


class HospitalAdmissionCharge(models.Model):
    """Unified charge ledger: every billable service (diagnostic, physiotherapy,
    dental, bed/ICU/NICU, oxygen, medicine, doctor fee...) lands here, whatever
    its source. Totals, statement and income reports all read from this one
    model. Auto charges carry a source_model/source_res_id for traceability;
    manual charges have no source."""
    _name = 'hospital.admission.charge'
    _description = 'Hospital Admission Charge'
    _order = 'date, id'

    admission_id = fields.Many2one(
        'hospital.admission', string='Admission', required=True,
        ondelete='cascade', index=True)
    service_type = fields.Selection(
        [('diagnostic', 'Diagnostic'),
         ('physiotherapy', 'Physiotherapy'),
         ('dental', 'Dental'),
         ('consultation', 'Consultation'),
         ('procedure', 'Procedure'),
         ('admission', 'Admission Charge'),
         ('bed', 'Bed'),
         ('cabin', 'Cabin'),
         ('icu', 'ICU'),
         ('nicu', 'NICU'),
         ('hdu', 'HDU'),
         ('oxygen', 'Oxygen'),
         ('medicine', 'Medicine'),
         ('doctor', 'Doctor Fee'),
         ('other', 'Other')],
        string='Service Type', required=True, default='other', index=True)
    item_id = fields.Many2one('examination.entry', string='Item')
    # The non-diagnostic counterpart of item_id: admission / ICU / NICU / other
    # ward charges are catalogued in admission.charge.item, not examination.entry.
    # Carried here so the income account can be resolved (and re-resolved) from
    # whichever catalogue the charge actually came from.
    charge_item_id = fields.Many2one('admission.charge.item', string='Charge Item')
    description = fields.Char('Description')
    unit_id = fields.Many2one(
        'diagnosis.department', string='Income Unit',
        help='Cost-center the income is attributed to (e.g. ICU, NICU, Physiotherapy). '
             'For oxygen, set this to the unit that gave the service.')
    provider_id = fields.Many2one('doctors.profile', string='Provider')
    qty = fields.Float('Qty', default=1.0)
    unit_price = fields.Float('Unit Price')
    discount = fields.Float('Discount')
    gross_amount = fields.Float(
        'Gross', compute='_compute_total_amount', store=True,
        help='Qty x Unit Price, before any discount. Income is recognised at '
             'this figure and the discount is posted separately, so the amount '
             'given away stays visible in the ledger.')
    total_amount = fields.Float('Total', compute='_compute_total_amount', store=True)
    date = fields.Datetime('Date', default=fields.Datetime.now)

    # Where this charge's revenue is credited. Seeded from the catalogue item
    # (examination.entry.accounts_id / admission.charge.item.accounts_id) when
    # the ledger is rebuilt, and left editable for the one-off charge that needs
    # a different account. Blank falls back to the default income account on the
    # hospital accounting settings.
    income_account_id = fields.Many2one(
        'account.account', string='Income Account',
        domain="[('account_type', '=', 'income')]",
        help='Revenue account credited for this charge at final settlement. '
             'Taken from the catalogue item; blank uses the default income '
             'account in Hospital Accounting Settings.')

    # traceability / idempotency for auto-generated charges
    source_model = fields.Char('Source Model', index=True)
    source_res_id = fields.Integer('Source Id', index=True)
    is_auto = fields.Boolean('Auto-generated', compute='_compute_is_auto', store=True)

    @api.depends('qty', 'unit_price', 'discount')
    def _compute_total_amount(self):
        for rec in self:
            rec.gross_amount = (rec.qty or 0.0) * (rec.unit_price or 0.0)
            rec.total_amount = rec.gross_amount - (rec.discount or 0.0)

    @api.onchange('item_id', 'charge_item_id')
    def _onchange_item_account(self):
        """Follow the catalogue when the item is changed by hand on the line."""
        for rec in self:
            account = rec._catalogue_account()
            if account:
                rec.income_account_id = account

    def _catalogue_account(self):
        """The income account this charge's catalogue item points at, if any.

        Diagnostics come from examination.entry, ward charges from
        admission.charge.item; both carry an ``accounts_id``.
        """
        self.ensure_one()
        account = self.item_id.accounts_id or self.charge_item_id.accounts_id
        if account:
            return account
        # The charge type's own default, so "every Team Charge credits this
        # head" is one setting rather than one per catalogue item.
        if self.charge_item_id.charge_type:
            return self.env['admission.charge.type'].search(
                [('code', '=', self.charge_item_id.charge_type)], limit=1).income_account_id
        return self.env['account.account']

    @api.depends('source_model')
    def _compute_is_auto(self):
        for rec in self:
            rec.is_auto = bool(rec.source_model)
