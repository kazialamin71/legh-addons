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
    description = fields.Char('Description')
    unit_id = fields.Many2one(
        'diagnosis.department', string='Income Unit',
        help='Cost-center the income is attributed to (e.g. ICU, NICU, Physiotherapy). '
             'For oxygen, set this to the unit that gave the service.')
    provider_id = fields.Many2one('doctors.profile', string='Provider')
    qty = fields.Float('Qty', default=1.0)
    unit_price = fields.Float('Unit Price')
    discount = fields.Float('Discount')
    total_amount = fields.Float('Total', compute='_compute_total_amount', store=True)
    date = fields.Datetime('Date', default=fields.Datetime.now)

    # traceability / idempotency for auto-generated charges
    source_model = fields.Char('Source Model', index=True)
    source_res_id = fields.Integer('Source Id', index=True)
    is_auto = fields.Boolean('Auto-generated', compute='_compute_is_auto', store=True)

    @api.depends('qty', 'unit_price', 'discount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = (rec.qty or 0.0) * (rec.unit_price or 0.0) - (rec.discount or 0.0)

    @api.depends('source_model')
    def _compute_is_auto(self):
        for rec in self:
            rec.is_auto = bool(rec.source_model)
