from odoo import _, api, fields, models
from odoo.exceptions import UserError

CARRIERS = (
    ('hospital.admission.charge', 'team_settlement_id'),
    ('bill.register.line', 'team_settlement_id'),
)


class TeamChargeSettlement(models.Model):
    """Paying a doctor what was collected on their behalf.

    Gathers every unsettled share for one doctor in a date range, records what
    was handed over, and stamps the lines so the same money cannot be paid
    twice. Under the off-ledger treatment this document *is* the record -- there
    is no journal entry behind it -- which is why it is a real document with a
    sequence and a state rather than a tick box.
    """
    _name = 'team.charge.settlement'
    _description = "Doctor's Share Settlement"
    _order = 'date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(default='New', readonly=True, copy=False)
    doctor_id = fields.Many2one(
        'doctors.profile', string='Doctor', required=True, index=True)
    date = fields.Date('Paid On', default=fields.Date.context_today, required=True)
    date_from = fields.Date('Charges From', required=True)
    date_to = fields.Date('Charges To', required=True,
                          default=fields.Date.context_today)
    collected_only = fields.Boolean(
        'Only what the patient has paid', default=True,
        help='On by default. Paying a doctor for money the patient never handed '
             'over leaves the hospital out of pocket, so that has to be a '
             'deliberate act rather than the default.')
    amount = fields.Float('Amount Paid', compute='_compute_amount', store=True)
    charge_count = fields.Integer(compute='_compute_amount', store=True)
    payment_note = fields.Char('Note')
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Paid'), ('cancel', 'Cancelled')],
        default='draft', required=True, copy=False, index=True)

    admission_charge_ids = fields.One2many(
        'hospital.admission.charge', 'team_settlement_id', string='Ward Charges',
        readonly=True)
    bill_line_ids = fields.One2many(
        'bill.register.line', 'team_settlement_id', string='Counter Charges',
        readonly=True)

    @api.depends('admission_charge_ids.team_amount', 'bill_line_ids.team_amount')
    def _compute_amount(self):
        for rec in self:
            charges = rec.admission_charge_ids
            lines = rec.bill_line_ids
            rec.amount = (sum(charges.mapped('team_amount'))
                          + sum(lines.mapped('team_amount')))
            rec.charge_count = len(charges) + len(lines)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'team.charge.settlement') or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    def _unsettled_domain(self, model):
        self.ensure_one()
        domain = [
            ('team_provider_id', '=', self.doctor_id.id),
            ('team_settlement_id', '=', False),
            ('team_amount', '>', 0),
        ]
        if model == 'hospital.admission.charge':
            domain += [('date', '>=', self.date_from),
                       ('date', '<=', self.date_to)]
        else:
            domain += [('bill_register_id.date', '>=', self.date_from),
                       ('bill_register_id.date', '<=', self.date_to)]
        return domain

    def action_collect(self):
        """Pull in everything outstanding for this doctor in the range."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only a draft settlement can gather charges.'))
        found = 0
        for model, _field in CARRIERS:
            records = self.env[model].search(self._unsettled_domain(model))
            if self.collected_only:
                records = records.filtered(lambda r: r._team_patient_paid())
            if records:
                records.with_context(team_settling=True).write(
                    {'team_settlement_id': self.id})
                found += len(records)
        if not found:
            raise UserError(_(
                'Nothing outstanding for %(doctor)s between %(start)s and '
                '%(end)s.', doctor=self.doctor_id.name,
                start=self.date_from, end=self.date_to))
        return True

    def action_done(self):
        for rec in self:
            if not rec.charge_count:
                raise UserError(_('Gather the charges before marking this paid.'))
            rec.state = 'done'
        return True

    def action_cancel(self):
        """Release the charges so they can be settled properly later."""
        for rec in self:
            rec.with_context(team_settling=True).write({'state': 'cancel'})
            for model, field in CARRIERS:
                self.env[model].search([(field, '=', rec.id)]).with_context(
                    team_settling=True).write({field: False})
        return True

    def action_draft(self):
        self.filtered(lambda r: r.state == 'cancel').write({'state': 'draft'})
        return True
