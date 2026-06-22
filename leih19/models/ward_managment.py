from odoo import models, fields

class WardManagment(models.Model):
    _name = 'ward.managment'
    _description = 'WardManagment'

    wname = fields.Char('Ward Name', required=True)
    bed = fields.Char('Bed No', required=True)
    name = fields.Char('Patient Name', required=True)
    pid = fields.Char('Patient ID', required=True)
    Date = fields.Datetime('Recived Date', required=True)
    precived = fields.Char('Recived By', required=True)
