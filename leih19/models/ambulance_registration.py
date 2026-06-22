from odoo import models, fields

class AmbulanceRegistration(models.Model):
    _name = 'ambulance.registration'
    _description = 'AmbulanceRegistration'

    vehicle_type = fields.Char('Vehicle Type', required=True)
    name = fields.Char('Vehicle Number', required=True)
    vehicle_name = fields.Char('Vehicle Name', required=True)
    active = fields.Boolean('In Service')
