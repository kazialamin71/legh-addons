from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ReferralDiscountMixin(models.AbstractModel):
    """The referral discount, and how it reaches the referrer's account.

    A referral discount is money the patient does not pay *because the referrer
    asked for it*, so the referrer funds it. It is carried to the settlement as
    one negative ``commission.line`` rather than by shaving each accrual,
    because every other way of doing it loses the audit trail: the per-item
    commission figures stay true to the MOU, the deduction is visible as its
    own row with its own amount, and gathering half a period into a settlement
    cannot accidentally take the deduction twice or not at all.
    """
    _name = 'commission.referral.discount.mixin'
    _description = 'Referral Discount Charge-back'

    def _referral_discount_referrer(self):
        """(doctor, broker) the discount is charged back to."""
        raise NotImplementedError

    def _referral_discount_amount(self):
        self.ensure_one()
        return self.referral_discount or 0.0

    @api.constrains('referral_discount')
    def _check_referral_discount_has_referrer(self):
        for rec in self:
            if (rec.referral_discount or 0.0) <= 0:
                continue
            doctor, broker = rec._referral_discount_referrer()
            if not doctor and not broker:
                raise ValidationError(_(
                    'A referral discount has to be charged back to someone, and '
                    '%s names no referring doctor and no referral. Set one, or '
                    'give the discount as Other Discount instead -- that one the '
                    'hospital pays for.', rec.display_name))

    def _accrue_referral_discount(self, field, today):
        """One negative accrual carrying the discount back to the referrer.

        Idempotent: re-settling an admission or re-confirming a bill updates the
        existing charge-back to the current amount rather than adding a second.
        """
        self.ensure_one()
        CommissionLine = self.env['commission.line'].sudo()
        existing = CommissionLine.search([
            (field, '=', self.id), ('is_referral_discount', '=', True),
        ], limit=1)
        amount = self._referral_discount_amount()
        doctor, broker = self._referral_discount_referrer()
        if amount <= 0 or (not doctor and not broker):
            # A discount taken back off the document must take its charge-back
            # with it, but only while nobody has settled it.
            if existing and existing.state == 'accrued':
                existing.unlink()
            return False
        vals = {
            field: self.id,
            'doctor_id': doctor.id if doctor else False,
            'broker_id': broker.id if broker else False,
            'is_referral_discount': True,
            'description': _('Referral discount'),
            'discount_amount': amount,
            'payable_amount': -amount,
            'accrual_date': today,
            'state': 'accrued',
        }
        if existing:
            if existing.state == 'accrued':
                existing.write(vals)
            return existing
        return CommissionLine.create(vals)
