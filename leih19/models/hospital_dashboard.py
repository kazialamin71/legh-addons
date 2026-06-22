from odoo import models, fields

class HospitalDashboard(models.Model):
    _name = 'hospital.dashboard'
    _description = 'HospitalDashboard'

    name = fields.Char('Name')
