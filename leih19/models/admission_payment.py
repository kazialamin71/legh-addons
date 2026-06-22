from odoo import models, fields

class AdmissionPayment(models.Model):
    _name = 'admission.payment'
    _description = 'AdmissionPayment'

    name = fields.Char('Cash COllection ID', readonly=True)
    admission_id = fields.Many2one('leih.admission', string='Admission ID', readoly=True)
    date = fields.Date('Date')
    amount = fields.Float('Receive Amount', required=True)
    payment_type = fields.Many2one('payment.type', string='Payment Type')
    service_charge = fields.Float('Service Charge')
    to_be_paid = fields.Float('To be Paid')
    account_number = fields.Char('Account No.')
    money_receipt_id = fields.Many2one('leih.money.receipt', string='Money Receipt ID')
