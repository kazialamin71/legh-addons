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

    def _team_budget(self):
        """The patient's money on this admission that no doctor has taken yet.

        This is what makes an early payout safe: the counter can hand a surgeon
        their fee the moment the patient's money covers it, and never more, and
        two surgeons on one admission cannot both be paid out of the same money.
        """
        self.ensure_one()
        paid_in = (self.paid or 0.0) + (self.investigation_paid or 0.0)
        paid_out = sum(self.charge_ids.mapped('team_paid'))
        return max(paid_in - paid_out, 0.0)

    def _rebuild_charges(self):
        """Never let a recalculation lose money already handed to a doctor.

        The rebuild deletes and recreates every charge it owns, which would wipe
        the running totals behind the doctor's payable -- the ledger would still
        say the doctor had been paid while the charges said they had not, and
        the next settlement would pay them again.
        """
        self.ensure_one()
        carried = {}
        for charge in self.charge_ids:
            if (charge.team_paid or 0.0) > 0.005 or (charge.team_entitled or 0.0) > 0.005:
                carried[(charge.source_model, charge.source_res_id)] = {
                    'team_paid': charge.team_paid,
                    'team_entitled': charge.team_entitled,
                    'team_settlement_id': charge.team_settlement_id.id,
                    'team_amount': charge.team_amount,
                    'team_provider_id': charge.team_provider_id.id,
                }
        res = super()._rebuild_charges()
        if not carried:
            return res
        pending = dict(carried)
        for charge in self.charge_ids:
            vals = pending.pop((charge.source_model, charge.source_res_id), None)
            if vals:
                charge.with_context(team_settling=True).write(vals)
        if pending:
            raise UserError(_(
                'Recalculating would drop %(count)s charge(s) that a doctor has '
                'already been paid for on admission %(name)s. Cancel the '
                'settlement first, or raise an adjusting charge instead of '
                'removing the original.',
                count=len(pending), name=self.name or ''))
        return res

    def _acc_post_release(self):
        """Recognise the hospital's income and the doctor's payable at release.

        This is where the split is decided, once, when the charges are finally
        known -- not guessed receipt by receipt on the way in::

            Dr Patient Advances       what the patient's money covers
            Dr Discount Allowed       discount given
            Dr Accounts Receivable    anything still owed
               Cr Income              hospital's share, per income head
               Cr Doctor's Payable    doctor's share, per doctor

        Diagnostics are left out: an admission-linked bill recognises its own
        income and its own doctor's share when it is confirmed.

        A share the counter already handed over before release was recognised
        then (``team_entitled``), so only the remainder is credited here.
        """
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled():
            return
        self.ensure_one()
        if self.acc_revenue_posted:
            return
        partner = self.patient_name.partner_id
        if not partner:
            return
        receivable = cfg._receivable_account(partner)

        native = self.charge_ids.filtered(
            lambda c: c.source_model != 'hospital.bill.line')
        income, team = {}, {}
        unaccounted = self.env['hospital.admission.charge']
        for charge in native:
            if charge.hospital_amount > 0:
                acct = cfg._charge_income_account(charge)
                if not acct:
                    unaccounted |= charge
                    continue
                income.setdefault(acct, 0.0)
                income[acct] += charge.hospital_amount
            owed = (charge.team_amount or 0.0) - (charge.team_entitled or 0.0)
            if owed > 0.005 and charge.team_provider_id:
                team.setdefault(charge.team_provider_id, 0.0)
                team[charge.team_provider_id] += owed
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

        hospital_total = sum(income.values())
        team_total = sum(team.values())
        if hospital_total <= 0 and team_total <= 0:
            self.acc_revenue_posted = True
            return

        # The discount comes out of the hospital's share: the doctor's cut was
        # agreed before the counter decided to be generous.
        discount = min(max(self.after_discount or 0.0, 0.0), max(hospital_total, 0.0))
        if discount and not cfg.discount_account_id:
            _logger.warning(
                '%s: a discount of %s cannot be posted because no "Discount '
                'Allowed" account is configured; it would land in receivables.',
                self.name, discount)
            discount = 0.0

        # What the patient still has to find, now that what the counter already
        # handed to the doctor has been taken out of their advance.
        patient_owes = hospital_total + team_total - discount
        advance = self._acc_open_advance() if cfg.advance_account_id else 0.0
        applied_advance = min(advance, patient_owes)
        ar_amount = patient_owes - applied_advance

        lines = []
        if applied_advance > 0:
            lines.append((cfg.advance_account_id, applied_advance, 0.0, partner))
        if discount > 0:
            lines.append((cfg.discount_account_id, discount, 0.0, partner))
        if ar_amount > 0.005 and receivable:
            lines.append((receivable, ar_amount, 0.0, partner))
        for acct, amt in income.items():
            lines.append((acct, 0.0, amt, partner))
        payable = cfg._team_payable_account() if team_total > 0 else False
        for doctor, amt in team.items():
            lines.append((payable, 0.0, amt, cfg._team_doctor_partner(doctor)))

        move = cfg._create_move(cfg.sales_journal_id, self.name, self.date,
                                lines, partner=partner)
        if move:
            self.acc_move_ids = [(4, move.id)]
            self.acc_revenue_posted = True
            # Recognised now, so a later payout only has to move the cash.
            for charge in native.filtered(
                    lambda c: c.team_amount > 0 and c.team_provider_id):
                charge.with_context(team_settling=True).team_entitled = charge.team_amount
