from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta
from num2words import num2words

class HospitalBillLine(models.Model):
    _name = "hospital.bill.line"
    _description = "Hospital Bill Line"

    name = fields.Char(string="Name")
    hospital_admission_id = fields.Many2one("hospital.admission", string="Hospital Admission")
    item_name = fields.Many2one("examination.entry", string="Item Name", ondelete="cascade")
    product_qty = fields.Float(string="Product Quantity", default=1.0)
    bill_created_date = fields.Datetime(string="Bill Created Date")
    delivery_date = fields.Date(string="Delivery Date")
    department = fields.Char(string="Department")
    date = fields.Datetime(string="Date", default=fields.Datetime.now, readonly=True)
    price = fields.Float(string="Price")
    discount = fields.Float(string="Discount (%)")
    flat_discount = fields.Integer(string="Flat Discount")
    total_discount = fields.Integer(string="Total Discount")
    discount_percent = fields.Integer(string="Discount Percent")
    total_amount = fields.Float(string="Total Amount")

    @api.onchange("item_name")
    def _onchange_item_name(self):
        for rec in self:
            if rec.item_name:
                required_days = rec.item_name.required_time or 0
                rec.department = rec.item_name.department.name if rec.item_name.department else False
                rec.price = rec.item_name.rate
                rec.total_amount = rec.item_name.rate
                rec.delivery_date = date.today() + timedelta(days=required_days)
                rec.product_qty = 1

    @api.onchange("price", "discount")
    def _onchange_discount(self):
        for rec in self:
            rec.total_amount = round(rec.price - (rec.price * rec.discount / 100.0))
            rec.total_discount = round(rec.price * rec.discount / 100.0)