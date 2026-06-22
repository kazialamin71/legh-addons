from odoo import models, fields

class HospitalPatientGuarantor(models.Model):
    _name = 'hospital.patient.guarantor'
    _description = 'HospitalPatientGuarantor'

    name = fields.Char('Guarantor Name')
    address = fields.Char('Address')
    relationship = fields.Char('Relationship')
    contact = fields.Char('Contact')
    email = fields.Char('Email')
    admission_id = fields.Many2one('hospital.admission', string='parent')
