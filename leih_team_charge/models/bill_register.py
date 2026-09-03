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

    # ------------------------------------------------------------------
    def _team_ratio(self):
        """Hospital's fraction of this bill, used to split a part payment.

        Pro-rata: every receipt is treated alike, so posted income rises
        smoothly with collection instead of arriving in a lump at the end, and
        no intermediate figure can exceed what the bill is worth.
        """
        self.ensure_one()
        total = sum(self.bill_register_line_id.mapped('total_amount'))
        if total <= 0:
            return 1.0
        return (self.hospital_charge_total or 0.0) / total

    def _acc_post_revenue(self):
        """Recognise the hospital's share only, when kept off the ledger."""
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled() or not cfg._team_off_ledger():
            return super()._acc_post_revenue()
        self.ensure_one()
        if self.acc_revenue_posted:
            return
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
        hospital_total = sum(income.values())
        # Same reasoning as the admission side: a bill-level discount that is
        # never posted quietly becomes an uncollectable receivable.
        line_total = sum(self.bill_register_line_id.mapped('total_amount'))
        discount = min(max(line_total - (self.grand_total or 0.0), 0.0), hospital_total)
        if discount and not cfg.discount_account_id:
            _logger.warning(
                '%s: a discount of %s cannot be posted because no "Discount '
                'Allowed" account is configured.', self.name, discount)
            discount = 0.0
        if hospital_total <= 0:
            # A bill that is entirely the doctor's earns the hospital nothing,
            # so there is genuinely no entry to make. Logged rather than passed
            # over in silence: this same branch once swallowed a bug that left
            # every bill marked posted with no journal entry behind it.
            _logger.info(
                '%s: nothing to post -- the hospital share of %s is zero across '
                '%s line(s).', self.name, self.grand_total,
                len(self.bill_register_line_id))
            self.acc_revenue_posted = True
            return
        lines = [(receivable, hospital_total - discount, 0.0, partner)]
        if discount > 0:
            lines.append((cfg.discount_account_id, discount, 0.0, partner))
        for acct, amt in income.items():
            lines.append((acct, 0.0, amt, partner))
        move = cfg._create_move(cfg.sales_journal_id, self.name, self.date,
                                lines, partner=partner)
        if move:
            self.acc_move_ids = [(4, move.id)]
            self.acc_revenue_posted = True

    def _acc_post_payment(self, amount, payment_type, date):
        """Bank only the hospital's slice of the receipt.

        The patient's receipt still shows the full amount; the doctor's slice
        never enters the ledger, which is the whole point of the treatment.
        How a part payment divides is the configured allocation policy -- under
        "doctor first" an early receipt produces no entry at all.
        """
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled() or not cfg._team_off_ledger():
            return super()._acc_post_payment(amount, payment_type, date)
        self.ensure_one()
        total = sum(self.bill_register_line_id.mapped('total_amount'))
        paid_now = self.paid or 0.0
        paid_before = paid_now - (amount or 0.0)
        team = self.team_charge_total or 0.0
        hospital_share = (cfg._team_cumulative_hospital(paid_now, total, team)
                          - cfg._team_cumulative_hospital(paid_before, total, team))
        if hospital_share <= 0:
            return
        return super()._acc_post_payment(hospital_share, payment_type, date)
