"""Printing the money receipt, at the moment the money is taken.

A counter hands the patient a receipt for every payment; there is no version of
this job where the receipt is optional. So the payment dialog's confirm button
*is* the print button, and the same action is on every historic payment line for
a reprint. Both go through ``ir.actions.report.report_action``, which
leih_printing intercepts and routes to whatever the cashier's "Print via"
setting says -- counter printer, browser dialog or download.
"""

from odoo import _, api, models
from odoo.exceptions import UserError


class LeihMoneyReceipt(models.Model):
    _inherit = 'leih.money.receipt'

    def action_print_receipt(self):
        self.ensure_one()
        report = self.env.ref('leih19.action_report_money_receipt', raise_if_not_found=False)
        if not report:
            raise UserError(_('The Money Receipt report is missing.'))
        return report.report_action(self)


class HospitalAdmissionPayment(models.Model):
    _inherit = 'hospital.admission.payment'

    def action_receive_and_print(self):
        """Confirm the payment and print its receipt.

        The record is saved by the form before this runs, and ``create`` is what
        raises the money receipt, so by the time we are here the receipt exists.
        """
        self.ensure_one()
        if not self.money_receipt_id:
            raise UserError(_(
                'No money receipt was created for this payment, so there is '
                'nothing to print.'))
        return self.money_receipt_id.action_print_receipt()


class GeneralAdmissionPaymentLine(models.Model):
    _inherit = 'general.admission.payment.line'

    def action_print_receipt(self):
        self.ensure_one()
        if not self.money_receipt_id:
            raise UserError(_('This payment line has no money receipt.'))
        return self.money_receipt_id.action_print_receipt()


class HospitalAdmission(models.Model):
    """Print the receipt for the advance taken when the admission was created.

    That payment never goes through the payment dialog -- ``create`` raises it
    from ``down_payment`` -- so without this the very first receipt is the one
    receipt nobody can print from the admission.
    """
    _inherit = 'hospital.admission'

    def action_print_last_receipt(self):
        self.ensure_one()
        receipt = self.money_receipt_ids.filtered(
            lambda m: m.state == 'confirm').sorted('id')[-1:]
        if not receipt:
            raise UserError(_('No payment has been taken on this admission yet.'))
        return receipt.action_print_receipt()
