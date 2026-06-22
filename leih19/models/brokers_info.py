from odoo import api, models, fields

class BrokersInfo(models.Model):
    _name = 'brokers.info'
    _description = 'BrokersInfo'
    _rec_name = 'broker_name'

    broker_id = fields.Char(string='Broker ID', readonly=True, copy=False, default='New')
    broker_name = fields.Char('Broker Name', required=True)
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], string='Status', default='active')
    commission_rate = fields.Float('Commission Rate (%) ')
    last_commission_calculation_date = fields.Date('Last Commission Calculation Date')
    bill_info = fields.One2many('bill.register', 'referral')
    doctor_ids = fields.Many2many('doctors.profile', 'referral_relation')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('broker_id', 'New') in ('New', False):
                vals['broker_id'] = self.env['ir.sequence'].next_by_code('brokers.info') or 'New'
        return super().create(vals_list)
