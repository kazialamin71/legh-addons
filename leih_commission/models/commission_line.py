from odoo import api, fields, models

class CommissionLine(models.Model):
    """One commission accrual: what a referrer earned on one billed item.

    The item is either a counter/investigation bill line or a charge on an
    admitted patient's ledger. Both live here so a settlement can gather a
    referrer's whole period in one pass, whatever the money came from.
    """
    _name = 'commission.line'
    _description = 'CommissionLine'
    _order = 'accrual_date desc, id desc'

    commission_line_ids = fields.Many2one('commission', string='Settlement', ondelete='set null')
    department_id = fields.Many2one('diagnosis.department', string='Department')
    name = fields.Many2one('examination.entry', string='Test Name')
    charge_item_id = fields.Many2one('admission.charge.item', string='Charge Item')
    is_referral_discount = fields.Boolean(
        'Referral Discount',
        help='A charge-back rather than an earning: the discount given on the '
             'referrer\'s account, carried as its own negative line so the '
             'settlement shows what was deducted and why instead of quietly '
             'shaving every item.')
    accommodation_category_id = fields.Many2one(
        'bed.category', string='Accommodation',
        help='Where the patient was lying when this charge was raised. Recorded '
             'because it is half of why this line earned the rate it did.')
    service_type = fields.Selection(
        selection=lambda self: self.env['hospital.admission.charge']._fields['service_type'].selection,
        string='Service Type')
    # Ward charges (a NICU bed, oxygen) have no catalogue record behind them at
    # all -- the charge line carries its own description -- so the accrual has
    # to keep one or it lists as a blank row.
    description = fields.Char('Item', compute='_compute_description', store=True, readonly=False)
    discount_amount = fields.Float('Discount Amount')
    test_amount = fields.Float('Test Amount')
    mou_payable_comm_var = fields.Float('MOU Payable Commission Amount (%)')
    mou_payable_comm_fixed = fields.Float('MOU Payable Commission Fixed')
    mou_payable_comm_max_cap = fields.Float('MOU Max CAP Amount')
    after_discount = fields.Float('After Discount Amount')
    payable_amount = fields.Float('Payable Amount')
    bill_line_id = fields.Many2one('bill.register.line', string='Bill Register Line ID')

    # --- Accrual tracking: one accrual per source line per referrer ---
    bill_id = fields.Many2one('bill.register', string='Bill', ondelete='cascade')
    admission_id = fields.Many2one('hospital.admission', string='Admission', ondelete='cascade')
    admission_charge_id = fields.Many2one(
        'hospital.admission.charge', string='Admission Charge', ondelete='cascade')
    doctor_id = fields.Many2one('doctors.profile', string='Doctor')
    broker_id = fields.Many2one('brokers.info', string='Broker')
    commission_configuration_id = fields.Many2one('commission.configuration', string='Commission Rule')
    accrual_date = fields.Datetime('Accrual Date')
    state = fields.Selection(
        [('accrued', 'Accrued'),
         ('settled', 'Settled'),
         ('paid', 'Paid'),
         ('cancelled', 'Cancelled')],
        string='Status', default='accrued', index=True)

    @api.depends('name', 'charge_item_id', 'admission_charge_id')
    def _compute_description(self):
        for rec in self:
            rec.description = (
                (rec.name and rec.name.name)
                or (rec.charge_item_id and rec.charge_item_id.name)
                or (rec.admission_charge_id and rec.admission_charge_id.description)
                or ''
            )
