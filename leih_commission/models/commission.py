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
    commission_line_ids = fields.One2many('commission.line', 'commission_line_ids')
    payment_ids = fields.One2many('commission.payment', 'cc_id', string='Payments')

    # What the referrer is actually owed, and what is left of it. Held apart
    # from total_amount because the earned figure and the agreed figure are
    # different things: the first is what the MOU produced, the second is what
    # was settled on after whatever was knocked off.
    adjustment_amount = fields.Float(
        'Deduction',
        help='Taken off before payment -- a round-down, an advance already '
             'given, an agreed write-off. Reduces what is owed; it does not '
             'touch the accruals behind it.')
    adjustment_reason = fields.Char('Deduction Reason')
    net_payable_amount = fields.Float(
        'Net Payable', compute='_compute_settlement_amounts', store=True)
    paid_amount = fields.Float(
        'Paid Amount', compute='_compute_settlement_amounts', store=True)
    balance_amount = fields.Float(
        'Balance', compute='_compute_settlement_amounts', store=True)
    state = fields.Selection(
        [('pending', 'Pending'),
         ('done', 'Confirmed'),
         ('partially_paid', 'Partially Paid'),
         ('paid', 'Paid & Close'),
         ('cancelled', 'Cancelled')],
        'Status', default='pending', readonly=True)

    @api.depends('total_amount', 'adjustment_amount',
                 'payment_ids.paid_amount', 'payment_ids.state')
    def _compute_settlement_amounts(self):
        for rec in self:
            rec.net_payable_amount = (rec.total_amount or 0.0) - (rec.adjustment_amount or 0.0)
            rec.paid_amount = sum(
                p.paid_amount or 0.0 for p in rec.payment_ids if p.state == 'done')
            rec.balance_amount = rec.net_payable_amount - rec.paid_amount

    def _recompute_settlement_totals(self):
        for rec in self:
            lines = rec.commission_line_ids
            # Accruals come from counter bills and from admitted patients, and
            # a settlement routinely holds both. Counting only the bills made
            # every admission invisible in the totals the payout is checked
            # against.
            bills = lines.mapped('bill_id')
            admissions = lines.mapped('admission_id')
            rec.total_amount = sum(lines.mapped('payable_amount'))
            rec.given_discount_amount = sum(lines.mapped('discount_amount'))
            rec.total_payable_amount = ((rec.total_amount or 0.0)
                                        - (rec.adjustment_amount or 0.0)
                                        - (rec.paid_amount or 0.0))
            rec.total_tests = len(lines)
            rec.total_bill = (sum(bills.mapped('grand_total'))
                              + sum(admissions.mapped('grand_total')))
            rec.total_patient = len(set(bills.mapped('patient_name').ids)
                                    | set(admissions.mapped('patient_name').ids))

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
        for rec in self:
            rec._recompute_settlement_totals()
        self.write({'state': 'done'})

    def action_register_payment(self):
        """Open a payment for whatever is still outstanding."""
        self.ensure_one()
        self._recompute_settlement_totals()
        if self.balance_amount <= 0:
            raise UserError(_('%s has nothing outstanding to pay.', self.name))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Commission Payment'),
            'res_model': 'commission.payment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_cc_id': self.id,
                'default_paid_amount': self.balance_amount,
            },
        }

    def action_settle_balance(self):
        """Pay off the remaining balance in one confirmed payment."""
        self.ensure_one()
        self._recompute_settlement_totals()
        if self.balance_amount <= 0:
            raise UserError(_('%s has nothing outstanding to pay.', self.name))
        payment = self.env['commission.payment'].create({
            'cc_id': self.id,
            'paid_amount': self.balance_amount,
            'date': fields.Date.context_today(self),
        })
        payment.action_confirm()
        self._update_payment_state()
        return True

    def _update_payment_state(self):
        """Move the settlement -- and its accruals -- to match what is paid.

        Driven by the balance rather than by a button, because the balance is
        the only thing that knows about part payments and deductions. The
        accruals follow: they read 'paid' when the referrer has actually been
        paid for them, and not one step earlier.
        """
        for rec in self:
            if rec.state in ('pending', 'cancelled'):
                continue
            rec._recompute_settlement_totals()
            if rec.net_payable_amount > 0 and rec.balance_amount <= 0.01:
                rec.state = 'paid'
                rec.commission_line_ids.write({'state': 'paid'})
            elif rec.paid_amount > 0:
                rec.state = 'partially_paid'
                rec.commission_line_ids.filtered(
                    lambda l: l.state == 'paid').write({'state': 'settled'})
            else:
                rec.state = 'done'
        return True

    def action_mark_paid(self):
        """Kept for the old button: settle whatever is left, then close."""
        for rec in self:
            if rec.balance_amount > 0:
                rec.action_settle_balance()
            else:
                rec._update_payment_state()
        return True

    def action_cancel(self):
        for rec in self:
            paid = rec.payment_ids.filtered(lambda p: p.state == 'done')
            if paid:
                raise UserError(_(
                    '%(name)s has %(count)s confirmed payment(s) against it. '
                    'Cancel those first -- releasing the accruals while the '
                    'money has gone out would let them be settled and paid a '
                    'second time.', name=rec.name, count=len(paid)))
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
