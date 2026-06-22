from odoo import models, fields

class AmbulanceExpense(models.Model):
    _name = 'ambulance.expense'
    _description = 'AmbulanceExpense'

    ambulance_id = fields.Many2one('ambulance.registration', string='Vehicle Name', required=True)
    fuel_cost = fields.Float('Fuel Cost')
    other_cost = fields.Float('Other Cost')
    description = fields.Text('Reason')
    state = fields.Selection([('draft', 'Pending'), ('confirm', 'Confirmed'), ('cancel', 'Cancelled')], 'Status', readonly=True, copy=False, select=True)
