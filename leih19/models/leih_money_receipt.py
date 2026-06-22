from odoo import api, models, fields

class LeihMoneyReceipt(models.Model):
    _name = 'leih.money.receipt'
    _description = 'LeihMoneyReceipt'
    _order = "id desc"

    name = fields.Char('MR ID', readonly=True, copy=False, default='New')
    date = fields.Date('Date')
    bill_id = fields.Many2one('bill.register', string='BIll ID')
    admission_id = fields.Many2one('leih.admission', string='Admission ID')
    general_admission_id = fields.Many2one('hospital.admission', string='General Admission ID')
    optics_sale_id = fields.Many2one('optics.sale', string='Optics Sale ID')
    amount = fields.Float('Paid Amount')
    bill_total_amount = fields.Float('Total Amount')
    due_amount = fields.Float('Due Amount')
    p_type = fields.Selection([('advance', 'Advance'), ('due_payment', 'Due Payment')], 'Payment Method')
    already_collected = fields.Boolean('Collected', default=False)
    diagonostic_bill = fields.Boolean('Diagonstic Bill')
    type = fields.Many2one('payment.type', string='Type')
    user_id = fields.Many2one('res.users', string='Current User', default=None)
    state = fields.Selection([('confirm', 'confirm'), ('cancel', 'Cancelled')], 'State', default='confirm')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New' or not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('leih.money.receipt') or 'New'
        return super().create(vals_list)
