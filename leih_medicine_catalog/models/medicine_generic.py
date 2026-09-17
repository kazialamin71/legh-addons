from odoo import api, fields, models


class MedicineGeneric(models.Model):
    """The molecule a brand is sold under: Paracetamol, Omeprazole, Ceftriaxone.

    One generic gathers every brand of it - Napa, Ace, Xpa are all Paracetamol -
    so a counter that is out of one brand can find the others without knowing
    the trade names, and a prescription written generically can be dispensed
    from whatever is on the shelf.
    """
    _name = 'medicine.generic'
    _description = 'Medicine Generic (Molecule)'
    _order = 'name'

    name = fields.Char('Generic Name', required=True, index=True)
    code = fields.Char('Code', help='Short code, if the pharmacy uses one.')
    strength_note = fields.Char(
        'Usual Strengths', help='Free note, e.g. "500 mg / 665 mg / suspension".')
    therapeutic_class = fields.Char(
        'Therapeutic Class', help='e.g. Analgesic, PPI, Cephalosporin.')
    note = fields.Text('Note')
    active = fields.Boolean(default=True)

    product_tmpl_ids = fields.One2many(
        'product.template', 'medicine_generic_id', string='Brands')
    product_count = fields.Integer(compute='_compute_product_count', string='Brands')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'That generic name already exists.'),
    ]

    @api.depends('product_tmpl_ids')
    def _compute_product_count(self):
        for rec in self:
            rec.product_count = len(rec.product_tmpl_ids)

    def action_view_products(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('medicine_generic_id', '=', self.id)],
            'context': {'default_medicine_generic_id': self.id},
        }
