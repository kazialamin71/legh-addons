from odoo import api, models, fields

class PaymentType(models.Model):
    _name = 'payment.type'
    _description = 'PaymentType'

    name = fields.Char('Name', required=True)
    account = fields.Many2one('account.account', string='Account', required=True)
    service_charge_account = fields.Many2one('account.account', string='Service Charge Account')
    service_charge = fields.Float('Service Charge', required=True)
    service_charge_flat = fields.Char('Service Charge(Flat)')
    active = fields.Boolean('Active')
    # Cash needs no card / bank / account number at the counter; every other
    # type does. Derived from the name so no extra configuration is required.
    is_cash = fields.Boolean('Cash Payment', compute='_compute_is_cash')

    @api.depends('name')
    def _compute_is_cash(self):
        for rec in self:
            rec.is_cash = (rec.name or '').strip().lower() == 'cash'
