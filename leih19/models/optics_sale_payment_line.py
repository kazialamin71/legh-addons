from odoo import models, fields

class OpticsSalePaymentLine(models.Model):
    _name = 'optics.sale.payment.line'
    _description = 'OpticsSalePaymentLine'

    optics_sale_payment_line_id = fields.Many2one('optics.sale', string='bill register payment')
    date = fields.Datetime('Date')
    amount = fields.Float('Amount')
    payment_type = fields.Many2one('payment.type', string='Payment Type')
    card_no = fields.Char('Card Number')
    bank_name = fields.Char('Bank Name')
    money_receipt_id = fields.Many2one('leih.money.receipt', string='Money Receipt ID')
