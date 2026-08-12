from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ExaminationSupportItem(models.Model):
    _name = 'examination.support.item'
    _description = 'Examination Supporting Item'
    _order = 'entry_id, id'

    entry_id = fields.Many2one(
        'examination.entry', string='Main Item',
        required=True, ondelete='cascade',
        help='The main examination item this supporting item belongs to.')
    support_entry_id = fields.Many2one(
        'examination.entry', string='Supporting Item',
        required=True, ondelete='restrict',
        help='Item automatically added to the bill together with the main item '
             '(e.g. disposable bed sheet, test tube). Its price comes from this '
             "item's own rate.")
    quantity = fields.Float('Quantity', default=1.0)
    rate = fields.Integer(
        related='support_entry_id.rate', string='Price', readonly=True,
        help='Unit price taken from the supporting item catalogue rate.')
    is_active = fields.Boolean(
        'Active', default=True,
        help='Only active supporting items are auto-added when billing the main item.')

    @api.constrains('entry_id', 'support_entry_id')
    def _check_not_self(self):
        for rec in self:
            if rec.support_entry_id and rec.support_entry_id == rec.entry_id:
                raise ValidationError(
                    "A supporting item cannot be the same as the main item.")
