from odoo import models, fields

class BillRegisterPaymentLine(models.Model):
    _name = 'bill.register.payment.line'
    _description = 'BillRegisterPaymentLine'

    bill_register_payment_line_id = fields.Many2one('bill.register', string='bill register payment')
    date = fields.Date('Date')
    amount = fields.Float('Amount')
    type = fields.Char('Type')
    card_no = fields.Char('Card Number')
    bank_name = fields.Char('Bank Name')
    money_receipt_id = fields.Many2one('leih.money.receipt', string='Money Receipt ID')
