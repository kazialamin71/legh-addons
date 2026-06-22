from odoo import models, fields

class DoctorsProfile(models.Model):
    _name = 'doctors.profile'
    _description = 'DoctorsProfile'

    name = fields.Char('Doctor Name', required=True)
    doctor_id = fields.Char('Doctor ID')
    department = fields.Char('Department')
    designation = fields.Char('Designation')
    degree = fields.Char('Degree')
    type = fields.Selection([('inhouse', 'In house'), ('consoled', 'Consoled'), ('prttime', 'Part Time'), ('outsid', 'Out Side')], string='Type', default='inhouse')
    status = fields.Selection([('active', 'Active'), ('inactive', 'Inactive')], string='Status', default='active')
    others = fields.Char('Others')
    bill_info = fields.One2many('bill.register', 'ref_doctors')
    admission_info = fields.Many2one('leih.admission', string='ref_doctors')
    ipd_visit = fields.Float('IPD Visit Fee')
    commission_rate = fields.Float('Commission Rate (%) ')
    last_commission_calculation_date = fields.Date('Last Commission Calculation Date')
    referral_id = fields.Many2one('doctors.profile', string='Referral ID')
    broker_ids = fields.Many2many('brokers.info', 'referral_relation')
    is_referral = fields.Boolean('Is Referral?')
