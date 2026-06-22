from odoo import models, fields

class OpticsSalePayment(models.Model):
    _name = 'optics.sale.payment'
    _description = 'OpticsSalePayment'

    name = fields.Char('Cash Collection ID', readonly=True)
    optics_sale_id = fields.Many2one('optics.sale', string='Optics Bill ID', readoly=True)
    date = fields.Date('Date', required=True)
    amount = fields.Float('Receive Amount', required=True)
    payment_type = fields.Many2one('payment.type', string='Payment Type')
    service_charge = fields.Float('Service Charge')
    to_be_paid = fields.Float('To be Paid')
    account_number = fields.Char('Account No.')
    money_receipt_id = fields.Many2one('leih.money.receipt', string='Money Receipt ID')
