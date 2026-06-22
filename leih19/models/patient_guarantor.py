from odoo import models, fields

class PatientGuarantor(models.Model):
    _name = 'patient.guarantor'
    _description = 'PatientGuarantor'

    name = fields.Char('Guarantor Name')
    address = fields.Char('Address')
    relationship = fields.Char('Relationship')
    contact = fields.Char('Contact')
    email = fields.Char('Email')
    admission_id = fields.Many2one('leih.admission', string='Admission')
