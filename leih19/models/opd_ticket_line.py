from odoo import api, fields, models

class OpdTicketLine(models.Model):
    _name = 'opd.ticket.line'
    _description = 'OpdTicketLine'

    name = fields.Many2one('opd.ticket.entry', string='Item Name', ondelete='cascade')
    opd_ticket_id = fields.Many2one('opd.ticket', string='Information')
    # Price / department / amount follow the chosen item but stay editable, so a
    # receptionist can still override the fee on a single ticket.
    price = fields.Integer('Price', compute='_compute_price', store=True, readonly=False)
    department = fields.Char('Department', compute='_compute_department', store=True, readonly=False)
    total_amount = fields.Integer('Total Amount', compute='_compute_total_amount', store=True, readonly=False)

    @api.depends('name')
    def _compute_price(self):
        for rec in self:
            rec.price = rec.name.fee if rec.name else rec.price

    @api.depends('name')
    def _compute_department(self):
        for rec in self:
            rec.department = rec.name.department.name if rec.name else rec.department

    @api.depends('price')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.price
