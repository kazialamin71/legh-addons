from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EmergencyPaymentWizard(models.TransientModel):
    """Take money against an ED case."""
    _name = 'emergency.payment.wizard'
    _description = 'Collect ED Payment'

    case_id = fields.Many2one(
        'emergency.case', string='ED Case', required=True,
        ondelete='cascade', readonly=True)
    total_charges = fields.Float(related='case_id.total_charges', readonly=True)
    already_paid = fields.Float(related='case_id.paid', readonly=True)
    due = fields.Float(related='case_id.due', readonly=True)
    amount = fields.Float('Amount to Collect')
    payment_type = fields.Many2one('payment.type', string='Payment Type')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        case = self.env['emergency.case'].browse(
            res.get('case_id') or self.env.context.get('default_case_id'))
        if case.exists():
            res.setdefault('amount', case.due)
            res.setdefault('payment_type', case.payment_type.id or False)
        return res

    def action_collect(self):
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_('Enter an amount greater than zero.'))
        self.case_id._register_ed_payment(self.amount, self.payment_type)
        return {'type': 'ir.actions.act_window_close'}
