from odoo import models, fields

class DiagnosisRoom(models.Model):
    _name = 'diagnosis.room'
    _description = 'DiagnosisRoom'

    room_no = fields.Char('Room No', required=True)
    name = fields.Char('Room Name', required=True)
    floor = fields.Char('Floor')
    building_name = fields.Char('Building Name')
