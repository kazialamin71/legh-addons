from odoo import api, fields, models


class EmergencyCaseCharge(models.Model):
    """Everything billable in the ED, in one ledger.

    Mirrors ``hospital.admission.charge`` so the two wards of the hospital are
    read the same way, with one addition the ED needs and admission does not: a
    ``product_id`` column. ED charges are dominated by consumables -- saline,
    cannula, gauze, sutures -- which are ``product.product`` records and have no
    entry in the examination catalogue, so a single item field could not carry
    both those and the investigations.
    """
    _name = 'emergency.case.charge'
    _description = 'Emergency Case Charge'
    _order = 'date, id'

    case_id = fields.Many2one(
        'emergency.case', string='ED Case', required=True,
        ondelete='cascade', index=True)
    charge_type = fields.Selection(
        [('consultation', 'Consultation'),
         ('procedure', 'Procedure'),
         ('consumable', 'Consumable'),
         ('medicine', 'Medicine'),
         ('investigation', 'Investigation'),
         ('observation', 'Observation / Bed'),
         ('oxygen', 'Oxygen'),
         ('ambulance', 'Ambulance'),
         ('other', 'Other')],
        string='Type', required=True, default='consumable', index=True)

    item_id = fields.Many2one(
        'examination.entry', string='Investigation / Service',
        help='From the examination catalogue. Used for investigations and '
             'priced services.')
    product_id = fields.Many2one(
        'product.product', string='Consumable / Medicine',
        help='Stock item handed out in the ED - saline, bandage, cannula, '
             'syringe, a strip of tablets.')
    description = fields.Char('Description', compute='_compute_description',
                              store=True, readonly=False)

    unit_id = fields.Many2one(
        'diagnosis.department', string='Income Unit',
        help='Cost-centre the income is attributed to.')
    provider_id = fields.Many2one('doctors.profile', string='Provider')

    qty = fields.Float('Qty', default=1.0)
    unit_price = fields.Float('Unit Price', compute='_compute_unit_price',
                              store=True, readonly=False)
    discount = fields.Float('Discount')
    total_amount = fields.Float('Total', compute='_compute_total_amount', store=True)
    date = fields.Datetime('Date', default=fields.Datetime.now)

    @api.depends('item_id', 'product_id')
    def _compute_description(self):
        for rec in self:
            if rec.item_id:
                rec.description = rec.item_id.name
            elif rec.product_id:
                rec.description = rec.product_id.display_name
            elif not rec.description:
                rec.description = False

    @api.depends('item_id', 'product_id')
    def _compute_unit_price(self):
        """Seed the price from the catalogue, but leave it editable.

        ED consumables are routinely given at a different rate (staff, waived,
        police case), so this is a starting point rather than a rule.
        """
        for rec in self:
            if rec.item_id:
                rec.unit_price = rec.item_id.rate
            elif rec.product_id:
                rec.unit_price = rec.product_id.lst_price

    @api.depends('qty', 'unit_price', 'discount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = (rec.qty or 0.0) * (rec.unit_price or 0.0) - (rec.discount or 0.0)

    @api.onchange('item_id')
    def _onchange_item_id(self):
        if self.item_id:
            self.product_id = False
            if self.item_id.department:
                self.unit_id = self.item_id.department
            if self.charge_type in ('consumable', 'medicine'):
                self.charge_type = 'investigation'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.item_id = False
            if self.charge_type in ('investigation', 'procedure'):
                self.charge_type = 'consumable'
