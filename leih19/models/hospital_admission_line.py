from odoo import api, fields, models


class HospitalAdmissionLine(models.Model):
    _name = "hospital.admission.line"
    _description = "Hospital Admission Line"

    # Items come from the admission charge catalogue (admission / ICU / NICU /
    # other). examination.entry is left to the diagnostic side of the system.
    name = fields.Many2one(
        "admission.charge.item", string="Item Name", ondelete="restrict")
    charge_type = fields.Selection(
        related="name.charge_type", string="Charge Type", store=True, readonly=True)
    leih_admission_id = fields.Many2one("hospital.admission", string="Admission")
    department = fields.Char(string="Department")
    product_qty = fields.Float(string="Quantity", default=1.0)
    price = fields.Float(string="Price")
    discount = fields.Float(string="Discount")
    flat_discount = fields.Integer(string="Flat Discount")
    total_discount = fields.Integer(string="Total Discount")
    discount_percent = fields.Integer(string="Discount Percent")
    total_amount = fields.Float(string="Total Amount")

    @api.onchange("name")
    def _onchange_name(self):
        for rec in self:
            if rec.name:
                rec.department = rec.name.department.name if rec.name.department else False
                rec.product_qty = rec.product_qty or 1
                rec.price = rec.name.rate
                rec.total_amount = rec.name.rate * (rec.product_qty or 1)

    @api.onchange("discount", "price", "product_qty")
    def _onchange_discount(self):
        for rec in self:
            rec.total_amount = round((rec.price - (rec.price * rec.discount / 100.0)) * rec.product_qty)

    @api.onchange("product_qty")
    def _onchange_qty(self):
        for rec in self:
            rec.total_amount = rec.price * rec.product_qty
