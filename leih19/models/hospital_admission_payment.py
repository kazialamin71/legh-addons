from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HospitalAdmissionPayment(models.Model):
    _name = "hospital.admission.payment"
    _description = "Admission Payment"

    name = fields.Char("Cash Collection ID", readonly=True, copy=False, default="New")
    admission_id = fields.Many2one(
        "hospital.admission",
        string="Admission ID",
        readonly=True,
    )
    date = fields.Date(string="Date", default=fields.Date.context_today)
    amount = fields.Float(string="Receive Amount", required=True)
    payment_type = fields.Many2one(
        "payment.type",
        string="Payment Type",
        default=lambda self: self._default_payment_type(),
    )
    service_charge = fields.Float(string="Service Charge")
    to_be_paid = fields.Float(string="To be Paid")
    account_number = fields.Char(string="Account No.")
    money_receipt_id = fields.Many2one(
        "leih.money.receipt",
        string="Money Receipt ID",
        readonly=True,
        copy=False,
    )

    @api.model
    def _default_payment_type(self):
        return self.env["payment.type"].search([("name", "=", "Cash")], limit=1)

    @api.model
    def create(self, vals):
        record = super().create(vals)

        if record.name in (False, "/", "New"):
            record.name = f"CC-100{record.id}"

        # Money receipt creation and paid/due update are handled by the
        # 'leih_admission' module (payments single source of truth).
        return record

    @api.onchange("payment_type", "amount")
    def _onchange_payment_type(self):
        for rec in self:
            rec.service_charge = 0.0
            rec.to_be_paid = rec.amount or 0.0

            if rec.payment_type and rec.payment_type.active:
                interest = rec.payment_type.service_charge or 0.0
                if interest > 0:
                    rec.service_charge = (rec.amount * interest) / 100.0
                    rec.to_be_paid = rec.amount + rec.service_charge

    def button_add_payment_action(self):
        account_move_obj = self.env["account.move"]
        journal_relation_obj = self.env["bill.journal.relation"]
        payment_line_obj = self.env["general.admission.payment.line"]

        for rec in self:
            if not rec.admission_id:
                raise UserError(_("Admission is required."))

            admission = rec.admission_id
            pay_amount = rec.amount or 0.0
            current_due = admission.due or 0.0
            current_paid = admission.paid or 0.0

            if pay_amount <= 0:
                raise UserError(_("Payment amount must be greater than zero."))

            service_line_vals = {
                "date": rec.date,
                "amount": pay_amount,
                "type": rec.payment_type.name if rec.payment_type else False,
                "card_no": rec.account_number,
                "admission_payment_line_id": admission.id,
                "money_receipt_id": rec.money_receipt_id.id,
            }
            service_line = payment_line_obj.create(service_line_vals)

            admission.write({
                "due": current_due - pay_amount,
                "paid": current_paid + pay_amount,
            })

            line_vals = []
            ref_name = admission.name or _("Admission Payment")

            if rec.payment_type and rec.payment_type.name == "Cash":
                line_vals.append((0, 0, {
                    "name": ref_name,
                    "account_id": 6,   # replace with proper configured account
                    "debit": pay_amount,
                    "credit": 0.0,
                }))
                line_vals.append((0, 0, {
                    "name": ref_name,
                    "account_id": 195,  # replace with proper configured receivable account
                    "debit": 0.0,
                    "credit": pay_amount,
                }))

            elif rec.payment_type and rec.payment_type.name == "Visa Card":
                other_method_pay = rec.to_be_paid or 0.0
                service_charge = rec.service_charge or 0.0

                if not rec.payment_type.account:
                    raise UserError(_("Please configure an account on the payment type."))

                line_vals.append((0, 0, {
                    "name": ref_name,
                    "account_id": rec.payment_type.account.id,
                    "debit": other_method_pay,
                    "credit": 0.0,
                }))
                line_vals.append((0, 0, {
                    "name": ref_name,
                    "account_id": 195,  # replace with proper configured receivable account
                    "debit": 0.0,
                    "credit": pay_amount,
                }))

                if service_charge > 0:
                    if not rec.payment_type.service_charge_account:
                        raise UserError(_("Please configure a service charge account on the payment type."))

                    line_vals.append((0, 0, {
                        "name": ref_name,
                        "account_id": rec.payment_type.service_charge_account.id,
                        "debit": 0.0,
                        "credit": service_charge,
                    }))

            else:
                raise UserError(_("Unsupported payment type."))

            move_vals = {
                "ref": ref_name,
                "date": rec.date or fields.Date.today(),
                "journal_id": 2,  # replace with proper configured journal
                "line_ids": line_vals,
            }

            move = account_move_obj.create(move_vals)
            move.action_post()

            journal_relation_obj.create({
                "journal_id": move.id,
                "general_admission_journal_relation_id": admission.id,
            })

        return True