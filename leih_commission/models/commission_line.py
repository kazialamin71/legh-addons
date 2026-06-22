from odoo import models, fields

class CommissionLine(models.Model):
    _name = 'commission.line'
    _description = 'CommissionLine'
    _order = 'accrual_date desc, id desc'

    commission_line_ids = fields.Many2one('commission', string='Settlement', ondelete='set null')
    department_id = fields.Many2one('diagnosis.department', string='Department')
    name = fields.Many2one('examination.entry', string='Test Name')
    discount_amount = fields.Float('Discount Amount')
    test_amount = fields.Float('Test Amount')
    mou_payable_comm_var = fields.Float('MOU Payable Commission Amount (%)')
    mou_payable_comm_fixed = fields.Float('MOU Payable Commission Fixed')
    mou_payable_comm_max_cap = fields.Float('MOU Max CAP Amount')
    after_discount = fields.Float('After Discount Amount')
    payable_amount = fields.Float('Payable Amount')
    bill_line_id = fields.Many2one('bill.register.line', string='Bill Register Line ID')

    # --- Accrual tracking (Phase 4): one accrual per source line per referrer ---
    bill_id = fields.Many2one('bill.register', string='Bill', ondelete='cascade')
    admission_id = fields.Many2one('hospital.admission', string='Admission', ondelete='cascade')
    doctor_id = fields.Many2one('doctors.profile', string='Doctor')
    broker_id = fields.Many2one('brokers.info', string='Broker')
    commission_configuration_id = fields.Many2one('commission.configuration', string='Commission Rule')
    accrual_date = fields.Datetime('Accrual Date')
    state = fields.Selection(
        [('accrued', 'Accrued'),
         ('settled', 'Settled'),
         ('paid', 'Paid'),
         ('cancelled', 'Cancelled')],
        string='Status', default='accrued', index=True)
