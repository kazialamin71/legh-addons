from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BillRegisterPayment(models.TransientModel):
    _name = 'bill.register.payment'
    _description = 'Bill Register Payment Wizard'

    name = fields.Char('Cash Collection ID', readonly=True)
    bill_id = fields.Many2one('bill.register', string='Bill ID', readonly=True)
    date = fields.Date(string='Payment Date', default=fields.Date.context_today)
    amount = fields.Float('Receive Amount', required=True)
    payment_type = fields.Many2one('payment.type', string='Payment Type', required=True)
    service_charge = fields.Float('Service Charge', compute='_compute_payment_amounts', store=True)
    to_be_paid = fields.Float('To be Paid', compute='_compute_payment_amounts', store=True)
    account_number = fields.Char('Account No.')
    money_receipt_id = fields.Many2one('leih.money.receipt', string='Money Receipt ID', readonly=True)

    @api.depends('amount', 'payment_type')
    def _compute_payment_amounts(self):
        for rec in self:
            rec.service_charge = 0.0
            rec.to_be_paid = rec.amount or 0.0

            if rec.payment_type and rec.payment_type.active:
                charge = rec.payment_type.service_charge or 0.0
                if charge > 0 and rec.amount:
                    rec.service_charge = (rec.amount * charge) / 100.0
                    rec.to_be_paid = rec.amount + rec.service_charge

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for rec in records:
            bill = rec.bill_id
            if not bill:
                raise UserError(_("Bill not found."))

            if bill.state == 'pending':
                raise UserError(_("Please confirm the bill first."))

            if bill.state == 'cancelled':
                raise UserError(_("Cancelled bill cannot receive payment."))

            if rec.amount <= 0:
                raise UserError(_("Receive amount must be greater than zero."))

            if rec.amount > (bill.due or 0.0):
                raise UserError(_("You cannot receive more than the unpaid amount."))

            # Money receipt + payment line; bill.paid / bill.due recompute from
            # the payment lines (no manual write).
            money_receipt = bill._register_payment(
                rec.amount, payment_type=rec.payment_type, date=rec.date,
            )
            rec.money_receipt_id = money_receipt.id

        return records