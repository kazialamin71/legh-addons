from odoo import api, fields, models


class Discount(models.Model):
    """bill.register.add_discount() passes context {'pi_id': bill.id} when
    opening this form, but bill_no never read it -- the discount always
    opened unlinked from the bill it was raised on."""
    _inherit = 'discount'

    bill_no = fields.Many2one(
        'bill.register', string='Bill No',
        default=lambda self: self.env.context.get('pi_id'))
