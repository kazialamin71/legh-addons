from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CommissionPayment(models.Model):
    """One payment made against a commission settlement.

    A settlement used to be paid in a single act: ``action_mark_paid`` wrote the
    whole total into ``paid_amount`` and there was nowhere to record that half
    of it went out in March and the rest in April. Payments are records now, so
    a settlement can be paid in instalments and each one keeps its own date,
    method and reference.
    """
    _name = 'commission.payment'
    _description = 'CommissionPayment'
    _order = 'date desc, id desc'

    name = fields.Char('CP No.', default='New', copy=False, readonly=True)
    cc_id = fields.Many2one(
        'commission', string='Settlement', ondelete='cascade', index=True)
    doctor_id = fields.Many2one('doctors.profile', string='Doctor',
                                related='cc_id.ref_doctors', store=True, readonly=True)
    broker_id = fields.Many2one('brokers.info', string='Broker',
                                related='cc_id.broker_id', store=True, readonly=True)
    date = fields.Date('Payment Date', default=fields.Date.context_today, required=True)
    paid_amount = fields.Float('Paid Amount', required=True)
    payment_type = fields.Many2one('payment.type', string='Payment Method')
    debit_id = fields.Many2one('account.account', string='Debit Account')
    credit_id = fields.Many2one('account.account', string='Credit Account')
    journal_id = fields.Many2one('account.move', string='Journal Entry')
    period_id = fields.Char('Period')
    note = fields.Text('Note')
    state = fields.Selection(
        [('pending', 'Draft'), ('done', 'Confirmed'), ('cancelled', 'Cancelled')],
        'Status', default='pending', readonly=True)

    # Kept because the old form showed it; it is the settlement's balance at the
    # time this payment was made, not a field the settlement reads back.
    due_amount = fields.Float('Balance After', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in ('New', False):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'commission.payment') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.state == 'done':
                continue
            if (rec.paid_amount or 0.0) <= 0:
                raise UserError(_('A payment has to be for more than nothing.'))
            balance = rec.cc_id.balance_amount if rec.cc_id else 0.0
            # Compared before this payment counts, so the message can say what
            # is actually left rather than what would be left afterwards.
            if rec.cc_id and rec.paid_amount > balance + 0.01:
                raise UserError(_(
                    'Settlement %(name)s has only %(balance).2f outstanding; '
                    'this payment is for %(amount).2f. Reduce it, or record a '
                    'deduction on the settlement if the difference is being '
                    'written off.',
                    name=rec.cc_id.name, balance=balance, amount=rec.paid_amount))
            rec.state = 'done'
            rec.due_amount = rec.cc_id.balance_amount if rec.cc_id else 0.0
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True

    def action_reset_to_draft(self):
        self.write({'state': 'pending'})
        return True
