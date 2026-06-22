from odoo import models, fields

class GeneralAdmissionRelease(models.Model):
    _name = 'general.admission.release'
    _description = 'GeneralAdmissionRelease'

    total = fields.Float('Total')
    paid = fields.Float('Paid')
    unpaid = fields.Float('Unpaid')
    admission_id = fields.Many2one('hospital.admission', string='Admission')
    pay = fields.Float('Pay')
    release_note = fields.Text('Release Note')
