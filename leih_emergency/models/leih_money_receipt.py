from odoo import fields, models


class LeihMoneyReceipt(models.Model):
    """Let a receipt point at an ED case.

    The receipt model already carries a column per collection point (bill,
    admission, optics); ED money goes through the same door so it reaches the
    cash collection reporting like everything else.
    """
    _inherit = 'leih.money.receipt'

    emergency_case_id = fields.Many2one(
        'emergency.case', string='ED Case', index=True, ondelete='cascade')
