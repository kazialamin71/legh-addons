from odoo import models, fields

class BillRegisterLine(models.Model):
    _name = 'bill.register.line'
    _description = 'BillRegisterLine'

    name = fields.Many2one('examination.entry', string='Item Name', ondelete='cascade')
    bill_register_id = fields.Many2one('bill.register', string='Information')
    department = fields.Char('Department')
    product_qty = fields.Float('Quantity')
    delivery_date = fields.Date('Delivery Date')
    date = fields.Datetime('Date', readonly=True, default=None)
    price = fields.Integer('Price')
    discount = fields.Integer('Discount (%)')
    flat_discount = fields.Integer('Flat Discount')
    total_discount = fields.Integer('Total Discount')
    discount_percent = fields.Integer('Discount Percent')
    total_amount = fields.Integer('Total Amount')
    assign_doctors = fields.Many2one('doctors.profile', string='Doctor')
    commission_paid = fields.Boolean('Commission Paid')
