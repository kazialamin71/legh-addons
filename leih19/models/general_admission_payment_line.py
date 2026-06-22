from odoo import models, fields

class GeneralAdmissionPaymentLine(models.Model):
    _name = 'general.admission.payment.line'
    _description = 'GeneralAdmissionPaymentLine'

    admission_payment_line_id = fields.Many2one('hospital.admission', string='admission payment')
    date = fields.Datetime('Date')
    amount = fields.Float('amount')
    type = fields.Char('Type')
    card_no = fields.Char('Card Number')
    bank_name = fields.Char('Bank Name')
    money_receipt_id = fields.Many2one('leih.money.receipt', string='Money Receipt ID')
