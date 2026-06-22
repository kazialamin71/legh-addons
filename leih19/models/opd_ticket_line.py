from odoo import models, fields

class OpdTicketLine(models.Model):
    _name = 'opd.ticket.line'
    _description = 'OpdTicketLine'

    name = fields.Many2one('opd.ticket.entry', string='Item Name', ondelete='cascade')
    opd_ticket_id = fields.Many2one('opd.ticket', string='Information')
    price = fields.Integer('Price')
    department = fields.Char('Department')
    total_amount = fields.Integer('Total Amount')
