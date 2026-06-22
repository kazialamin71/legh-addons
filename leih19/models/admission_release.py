from odoo import models, fields

class AdmissionRelease(models.Model):
    _name = 'admission.release'
    _description = 'AdmissionRelease'

    total = fields.Float('Total')
    paid = fields.Float('Paid')
    unpaid = fields.Float('Unpaid')
    admission_id = fields.Many2one('leih.admission', string='Admission')
    pay = fields.Float('Pay')
    release_note = fields.Text('Release Note')
