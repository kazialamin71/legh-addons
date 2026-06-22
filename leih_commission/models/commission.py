from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Commission(models.Model):
    _name = 'commission'
    _description = 'Commission'

    name = fields.Char('Commission Calculation', default='New', copy=False, readonly=True)
    ref_doctors = fields.Many2one('doctors.profile', string='Doctor')
    broker_id = fields.Many2one('brokers.info', string='Broker')
    commission_configuration_id = fields.Many2one('commission.configuration', string='Commission Rule')
    commission_rate = fields.Float('Commission Rate')
    cal_st_date = fields.Datetime('Calculation Start Date', required=True)
    cal_end_date = fields.Datetime('Calculation End Date', required=True)
    total_amount = fields.Float('Total Commission Amount')
    given_discount_amount = fields.Float('Total Discount')
    total_payable_amount = fields.Float('Total Payable Amount')
    total_patient = fields.Float('Total Patients')
    total_bill = fields.Float('Total Billing Amount')
    total_tests = fields.Float('Total Tests in All Billing')
    paid_amount = fields.Float('Paid Amount')
    commission_line_ids = fields.One2many('commission.line', 'commission_line_ids')
    state = fields.Selection([('pending', 'Pending'), ('done', 'Confirmed'), ('paid', 'Paid & Close'), ('cancelled', 'Cancelled')], 'Status', default='pending', readonly=True)

    def _recompute_settlement_totals(self):
        for rec in self:
            lines = rec.commission_line_ids
            bills = lines.mapped('bill_id')
            rec.total_amount = sum(lines.mapped('payable_amount'))
            rec.given_discount_amount = sum(lines.mapped('discount_amount'))
            rec.total_payable_amount = (rec.total_amount or 0.0) - (rec.paid_amount or 0.0)
            rec.total_tests = len(lines)
            rec.total_bill = sum(bills.mapped('grand_total'))
            rec.total_patient = len(bills.mapped('patient_name'))

    def action_gather_accruals(self):
        """Pull all un-settled accrued commission lines for this doctor within
        the calculation period into this settlement."""
        self.ensure_one()
        if not self.ref_doctors and not self.broker_id:
            raise UserError(_("Set the Doctor or Broker before gathering accruals."))
        domain = [
            ('state', '=', 'accrued'),
            ('commission_line_ids', '=', False),
        ]
        if self.ref_doctors:
            domain.append(('doctor_id', '=', self.ref_doctors.id))
        else:
            domain.append(('broker_id', '=', self.broker_id.id))
        if self.cal_st_date:
            domain.append(('accrual_date', '>=', self.cal_st_date))
        if self.cal_end_date:
            domain.append(('accrual_date', '<=', self.cal_end_date))
        lines = self.env['commission.line'].search(domain)
        if not lines:
            raise UserError(_("No un-settled accruals found for this doctor in the selected period."))
        lines.write({'commission_line_ids': self.id, 'state': 'settled'})
        self._recompute_settlement_totals()
        return True

    def action_confirm(self):
        self.write({'state': 'done'})

    def action_mark_paid(self):
        for rec in self:
            rec._recompute_settlement_totals()
            rec.paid_amount = rec.total_amount
            rec.total_payable_amount = 0.0
            rec.commission_line_ids.write({'state': 'paid'})
        self.write({'state': 'paid'})

    def action_cancel(self):
        for rec in self:
            # release settled lines back to the accrual pool
            rec.commission_line_ids.filtered(lambda l: l.state in ('settled', 'paid')).write({
                'commission_line_ids': False, 'state': 'accrued',
            })
        self.write({'state': 'cancelled'})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in ('New', False):
                vals['name'] = self.env['ir.sequence'].next_by_code('commission') or 'New'
        return super().create(vals_list)
