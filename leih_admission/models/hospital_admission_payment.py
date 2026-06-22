from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HospitalAdmissionPayment(models.Model):
    """Route the admission payment wizard through the single payment helper:
    a money receipt is created and ``paid``/``due`` recompute from it. No manual
    paid writes, no raw SQL."""
    _inherit = 'hospital.admission.payment'

    @api.model
    def create(self, vals):
        record = super().create(vals)
        admission = record.admission_id
        if not admission:
            raise UserError(_("Admission is required."))
        if admission.state in ('pending', 'cancelled'):
            raise UserError(_("Please confirm the admission before taking a payment."))
        if (record.amount or 0.0) <= 0:
            raise UserError(_("Payment amount must be greater than zero."))
        # Overpayment (advance deposit) is allowed for admissions.

        mr = admission._register_admission_payment(
            record.amount,
            payment_type=record.payment_type,
            date=record.date,
            account_number=record.account_number,
        )
        record.money_receipt_id = mr.id
        return record
