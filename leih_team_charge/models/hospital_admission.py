import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HospitalAdmission(models.Model):
    """Admission totals, and recognising only the hospital's earnings."""
    _inherit = 'hospital.admission'

    team_charge_total = fields.Float(
        "Doctors' Share", compute='_compute_team_totals', store=True)
    hospital_charge_total = fields.Float(
        'Hospital Share', compute='_compute_team_totals', store=True)
    team_unassigned_count = fields.Integer(
        compute='_compute_team_totals', store=True,
        help="Charges whose item carries a doctor's share with nobody named.")

    @api.depends('charge_ids.team_amount', 'charge_ids.hospital_amount',
                 'charge_ids.team_unassigned')
    def _compute_team_totals(self):
        for rec in self:
            rec.team_charge_total = sum(rec.charge_ids.mapped('team_amount'))
            rec.hospital_charge_total = sum(rec.charge_ids.mapped('hospital_amount'))
            rec.team_unassigned_count = len(rec.charge_ids.filtered('team_unassigned'))

    def action_calculate_payable(self):
        """Rebuild the charges, then make sure the form shows the new figures.

        The rebuild deletes and recreates every charge line, so the record the
        browser is holding no longer describes what is in the database. Without
        an explicit reload the desk sees the previous figures and presses the
        button again, which is exactly what it looked like when the doctor's
        share appeared only on the second or third press.
        """
        res = super().action_calculate_payable()
        self.env.flush_all()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.admission',
            'res_id': self[:1].id,
            'view_mode': 'form',
            'target': 'current',
        } if len(self) == 1 else res

    def _acc_post_release(self):
        """Recognise the hospital's share only, when kept off the ledger.

        Mirrors the base method exactly -- native charges only, advance applied
        first, receivable for the remainder -- but every figure is the
        hospital's half rather than the whole charge.
        """
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled() or not cfg._team_off_ledger():
            return super()._acc_post_release()
        self.ensure_one()
        if self.acc_revenue_posted:
            return
        partner = self.patient_name.partner_id
        if not partner:
            return
        receivable = cfg._receivable_account(partner)

        # Before anything is recognised, make the advance account tell the truth
        # about how much of what was taken is actually the hospital's.
        self._acc_true_up_advance(cfg)

        native = self.charge_ids.filtered(
            lambda c: c.source_model != 'hospital.bill.line')
        income = {}
        unaccounted = self.env['hospital.admission.charge']
        for charge in native:
            if charge.hospital_amount <= 0:
                continue
            # Full resolution, same as the base poster: the charge's own head
            # (catalogue item, bed or doctor), then the service-type map, then
            # the default. Reading only ``item_id`` -- which bed, ward and
            # pharmacy charges never have -- sent every one of them to the
            # default income account and collapsed the whole ward P&L into it.
            acct = cfg._charge_income_account(charge)
            if not acct:
                unaccounted |= charge
                continue
            income.setdefault(acct, 0.0)
            income[acct] += charge.hospital_amount
        if unaccounted:
            raise UserError(_(
                'These charges have no income account, so admission %(name)s '
                'cannot be posted to the general ledger:\n\n%(rows)s\n\n'
                'Set an account on the catalogue item, the bed or the doctor, or '
                'map the service type under Accounting > Configuration > '
                'Hospital Accounting.',
                name=self.name or '',
                rows='\n'.join(
                    '  - %s (%s)' % (c.description or '/',
                                     dict(c._fields['service_type'].selection).get(c.service_type))
                    for c in unaccounted)))
        native_total = sum(income.values())
        if native_total <= 0:
            self.acc_revenue_posted = True
            return

        # Advances are banked net of the doctor's share and trued up above, so
        # what the advance account holds for this patient is hospital money only.
        # A discount is a real reduction of what the hospital earns, and it has
        # to be posted somewhere. Left out, the entry still balances only
        # because the difference is dumped into Accounts Receivable -- a debt
        # the patient does not owe and will never pay, while income stands
        # overstated by the whole discount.
        #
        # The hospital absorbs it: the doctor's share was agreed before the
        # counter decided to be generous. Capped at the hospital's own income so
        # a discount larger than the hospital's share cannot push it negative.
        discount = min(max(self.after_discount or 0.0, 0.0), native_total)
        if discount and not cfg.discount_account_id:
            _logger.warning(
                '%s: a discount of %s cannot be posted because no "Discount '
                'Allowed" account is configured; it would land in receivables.',
                self.name, discount)
            discount = 0.0
        patient_owes = native_total - discount

        advance = self.acc_hospital_advance or 0.0 if cfg.advance_account_id else 0.0
        applied_advance = min(advance, patient_owes)
        ar_amount = patient_owes - applied_advance

        lines = []
        for acct, amt in income.items():
            lines.append((acct, 0.0, amt, partner))
        if discount > 0:
            lines.append((cfg.discount_account_id, discount, 0.0, partner))
        if applied_advance > 0:
            lines.append((cfg.advance_account_id, applied_advance, 0.0, partner))
        if ar_amount > 0 and receivable:
            lines.append((receivable, ar_amount, 0.0, partner))
        move = cfg._create_move(cfg.sales_journal_id, self.name, self.date,
                                lines, partner=partner)
        if move:
            self.acc_move_ids = [(4, move.id)]
            self.acc_revenue_posted = True

    acc_hospital_advance = fields.Float(
        'Advance Banked as Hospital', readonly=True, copy=False,
        help='How much of the advances taken has been posted as hospital money. '
             'Reconciled against the final split when the admission is released.')

    def _team_ratio(self):
        """Hospital's fraction of this admission, for splitting a receipt.

        Returns 1.0 while there are no charges yet -- an advance taken on the
        day of admission is provisionally all the hospital's, because nothing is
        yet known about what it will be spent on. `_acc_true_up_advance` fixes
        that at release, once the split is finally known.
        """
        self.ensure_one()
        total = sum(self.charge_ids.mapped('total_amount'))
        if total <= 0:
            return 1.0
        return (self.hospital_charge_total or 0.0) / total

    def _team_charge_base(self):
        """(total charged, doctor's share) for the allocation maths."""
        self.ensure_one()
        return (sum(self.charge_ids.mapped('total_amount')),
                self.team_charge_total or 0.0)

    def _team_hospital_slice(self, amount):
        """The hospital's part of one payment, under the configured policy.

        `paid` already includes this payment by the time the posting hook runs,
        so the slice is the cumulative figure now minus the cumulative figure
        before this money arrived.
        """
        self.ensure_one()
        cfg = self.env['leih.accounting.config']._get()
        total, team = self._team_charge_base()
        paid_now = self.paid or 0.0
        paid_before = paid_now - (amount or 0.0)
        return (cfg._team_cumulative_hospital(paid_now, total, team)
                - cfg._team_cumulative_hospital(paid_before, total, team))

    def _acc_post_advance(self, amount, payment_type, date):
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled() or not cfg._team_off_ledger():
            return super()._acc_post_advance(amount, payment_type, date)
        self.ensure_one()
        hospital_share = self._team_hospital_slice(amount)
        if hospital_share <= 0:
            # Under "doctor first" this is the normal case early on: the money
            # collected so far is all the doctor's, so there is nothing for the
            # hospital to bank and no entry to make.
            return
        before = self.acc_move_ids
        res = super()._acc_post_advance(hospital_share, payment_type, date)
        if self.acc_move_ids == before:
            # The base method bails silently when the advance account or the
            # cash account is not configured. Counting money it never posted
            # would make the release true-up correct an entry that does not
            # exist, so only what actually reached the ledger is tallied.
            _logger.warning(
                '%s: advance of %s produced no journal entry -- check that '
                '"Advance Account" is set on the hospital accounting settings.',
                self.name, hospital_share)
            return res
        self.acc_hospital_advance = (self.acc_hospital_advance or 0.0) + hospital_share
        return res

    def _acc_true_up_advance(self, cfg):
        """Correct advances that were banked before the split was knowable.

        A patient pays 20,000 on the day they are admitted. No charges exist
        yet, so the whole 20,000 is banked as hospital money. By the time they
        leave, the charges say only 20 percent of it ever was -- the other
        16,000 is the doctor's, and it has to leave the hospital's books, or it
        sits in the advance account for ever and every future reconciliation is
        wrong by that amount.

        Posted as a real movement of cash rather than a silent correction,
        because that is what it is: money taken at the counter and handed on.
        """
        self.ensure_one()
        total, team = self._team_charge_base()
        target = cfg._team_cumulative_hospital(self.paid or 0.0, total, team)
        posted = self.acc_hospital_advance or 0.0
        difference = target - posted
        if abs(difference) < 0.01 or not cfg.advance_account_id:
            return
        journal, cash_account = cfg._payment_accounts(self.payment_type)
        partner = self.patient_name.partner_id
        if not journal or not cash_account:
            return
        if difference < 0:
            # Over-banked: the excess is the doctor's and leaves as cash.
            lines = [(cfg.advance_account_id, -difference, 0.0, partner),
                     (cash_account, 0.0, -difference, False)]
        else:
            lines = [(cash_account, difference, 0.0, False),
                     (cfg.advance_account_id, 0.0, difference, partner)]
        move = cfg._create_move(journal, '%s (advance adjustment)' % self.name,
                                fields.Date.context_today(self), lines,
                                partner=partner)
        if move:
            self.acc_move_ids = [(4, move.id)]
            self.acc_hospital_advance = target
