import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class BillRegisterLine(models.Model):
    """The counter side of the split.

    Same arithmetic as a ward charge -- a dressing does not become a different
    thing because it was billed at a desk.
    """
    _name = 'bill.register.line'
    _inherit = ['bill.register.line', 'team.charge.mixin']

    def _team_item(self):
        self.ensure_one()
        return self.name

    def _team_default_provider(self):
        self.ensure_one()
        return self.assign_doctors or self.bill_register_id.ref_doctors

    def _team_gross(self):
        self.ensure_one()
        return self.gross_amount or 0.0

    def _team_net(self):
        self.ensure_one()
        return self.total_amount or 0.0

    def _team_qty(self):
        self.ensure_one()
        return self.product_qty or 0.0

    def _team_document(self):
        self.ensure_one()
        return self.bill_register_id

    @api.depends('assign_doctors', 'bill_register_id.ref_doctors')
    def _compute_team_provider_id(self):
        return super()._compute_team_provider_id()

    @api.depends('name', 'team_provider_id')
    def _compute_team_share_rule(self):
        return super()._compute_team_share_rule()

    @api.depends('gross_amount', 'total_amount', 'product_qty',
                 'team_share_method', 'team_share_value')
    def _compute_team_amount(self):
        return super()._compute_team_amount()

    @api.depends('total_amount', 'team_amount')
    def _compute_hospital_amount(self):
        return super()._compute_hospital_amount()

    @api.depends('team_provider_id', 'name')
    def _compute_team_unassigned(self):
        return super()._compute_team_unassigned()


class BillRegister(models.Model):
    """Bill totals, and posting only what the hospital actually earned."""
    _inherit = 'bill.register'

    team_charge_total = fields.Float(
        "Doctors' Share", compute='_compute_team_totals', store=True)
    hospital_charge_total = fields.Float(
        'Hospital Share', compute='_compute_team_totals', store=True)
    team_unassigned_count = fields.Integer(
        compute='_compute_team_totals', store=True,
        help="Lines whose item carries a doctor's share with nobody named.")

    @api.depends('bill_register_line_id.team_amount',
                 'bill_register_line_id.hospital_amount',
                 'bill_register_line_id.team_unassigned')
    def _compute_team_totals(self):
        for rec in self:
            rec.team_charge_total = sum(rec.bill_register_line_id.mapped('team_amount'))
            rec.hospital_charge_total = sum(rec.bill_register_line_id.mapped('hospital_amount'))
            rec.team_unassigned_count = len(rec.bill_register_line_id.filtered('team_unassigned'))

    def _team_budget(self):
        """The patient's money on this bill that no doctor has taken yet."""
        self.ensure_one()
        paid_out = sum(self.bill_register_line_id.mapped('team_paid'))
        return max((self.paid or 0.0) - paid_out, 0.0)

    # ------------------------------------------------------------------
    # Posting
    # ------------------------------------------------------------------
    def _acc_post_revenue(self):
        """Recognise the hospital's income and the doctor's payable together.

        A counter bill has no final settlement to wait for -- it recognises its
        income the moment it is confirmed -- so the doctor's share becomes a
        payable at the same instant::

            Dr Accounts Receivable   grand total
            Dr Discount Allowed      bill-level discount
               Cr Income             hospital's share, per income head
               Cr Doctor's Payable    doctor's share, per doctor

        The patient owes the whole bill either way; what changes is that the
        part of it that is the doctor's is a liability rather than income.
        """
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled():
            return
        self.ensure_one()
        if self.acc_revenue_posted:
            return
        # Deliberately NOT delegating to the base poster when no doctor share
        # is involved. The base defers an admission-linked bill's income to the
        # admission's settlement entry -- but the settlement here excludes
        # hospital.bill.line charges, because a bill recognises its own income.
        # Delegating would leave that income recognised in neither place.
        partner = self.patient_name.partner_id
        receivable = cfg._receivable_account(partner) if partner else False
        if not partner or not receivable:
            return

        income = {}
        for line in self.bill_register_line_id:
            if line.hospital_amount <= 0:
                continue
            acct = cfg._income_account(line.name) or cfg.default_income_account_id
            if not acct:
                continue
            income.setdefault(acct, 0.0)
            income[acct] += line.hospital_amount
        team = {}
        for line in self.bill_register_line_id.filtered(lambda l: l.team_amount > 0):
            if not line.team_provider_id:
                continue
            team.setdefault(line.team_provider_id, 0.0)
            team[line.team_provider_id] += line.team_amount
        hospital_total = sum(income.values())
        team_total = sum(team.values())
        if hospital_total <= 0 and team_total <= 0:
            _logger.info('%s: nothing to post -- no hospital or doctor share.', self.name)
            self.acc_revenue_posted = True
            return

        line_total = sum(self.bill_register_line_id.mapped('total_amount'))
        grand = self.grand_total or 0.0
        discount = max(line_total - grand, 0.0)
        if discount and not cfg.discount_account_id:
            # Without a contra account the discount has to come out of income,
            # which is the netting this design avoids -- but an unbalanced entry
            # is worse, so it is absorbed and said out loud.
            _logger.warning(
                '%s: a discount of %s cannot be posted because no "Discount '
                'Allowed" account is configured; it is being netted off income.',
                self.name, discount)
            if hospital_total > 0:
                factor = max(hospital_total - discount, 0.0) / hospital_total
                income = {a: v * factor for a, v in income.items()}
                hospital_total = sum(income.values())
            discount = 0.0

        # The patient owes the whole bill: the hospital's share plus the
        # doctor's, less whatever was let off.
        lines = [(receivable, hospital_total + team_total - discount, 0.0, partner)]
        if discount > 0:
            lines.append((cfg.discount_account_id, discount, 0.0, partner))
        for acct, amt in income.items():
            lines.append((acct, 0.0, amt, partner))
        payable = cfg._team_payable_account() if team_total > 0 else False
        for doctor, amt in team.items():
            lines.append((payable, 0.0, amt, cfg._team_doctor_partner(doctor)))
        move = cfg._create_move(cfg.sales_journal_id, self._acc_move_ref(), self.date,
                                lines, partner=partner)
        if move:
            self.acc_move_ids = [(4, move.id)]
            self.acc_revenue_posted = True
            # Recognised now, so a later payout only has to move the cash.
            for line in self.bill_register_line_id.filtered(
                    lambda l: l.team_amount > 0 and l.team_provider_id):
                line.with_context(team_settling=True).team_entitled = line.team_amount
