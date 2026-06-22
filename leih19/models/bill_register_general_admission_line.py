from odoo import models, fields
from odoo import api, fields, models, _

class BillRegisterGeneralAdmissionLine(models.Model):
    _name = 'bill.register.general.admission.line'
    _description = 'BillRegisterGeneralAdmissionLine'

    general_admission_line_id = fields.Many2one('hospital.admission', string='admission')
    bill_id = fields.Many2one('bill.register', string='Bill ID')
    total = fields.Float('Total')

    @api.onchange("bill_id")
    def _onchange_bill_id(self):
        for rec in self:
            if rec.bill_id:
                rec.total = rec.bill_id.total

