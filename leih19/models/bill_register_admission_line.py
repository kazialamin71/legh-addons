from odoo import models, fields

class BillRegisterAdmissionLine(models.Model):
    _name = 'bill.register.admission.line'
    _description = 'BillRegisterAdmissionLine'

    admission_line_id = fields.Many2one('leih.admission', string='admission')
    bill_id = fields.Many2one('bill.register', string='Bill ID')
    total = fields.Float('Total')
