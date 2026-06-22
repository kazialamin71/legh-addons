from odoo import models, fields

class PaymentType(models.Model):
    _name = 'payment.type'
    _description = 'PaymentType'

    name = fields.Char('Name', required=True)
    account = fields.Many2one('account.account', string='Account', required=True)
    service_charge_account = fields.Many2one('account.account', string='Service Charge Account')
    service_charge = fields.Float('Service Charge', required=True)
    service_charge_flat = fields.Char('Service Charge(Flat)')
    active = fields.Boolean('Active')
