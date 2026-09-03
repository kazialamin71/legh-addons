from odoo import fields, models


class LeihAccountingConfig(models.Model):
    _inherit = 'leih.accounting.config'

    team_charge_treatment = fields.Selection(
        [('off_ledger', "Keep it out of the ledger entirely"),
         ('liability', 'Post it as a payable to the doctor')],
        string="Doctor's Share Treatment", default='off_ledger', required=True,
        help="Out of the ledger: only the hospital's share is ever posted, so "
             "the doctor's share appears in neither the profit and loss nor the "
             "trial balance. What the doctor is owed is tracked in the Team "
             "Charge reports instead.\n"
             "As a payable: the full amount is posted, with the doctor's share "
             "credited to a liability account. Income is the hospital's share "
             "either way.")
    team_payable_account_id = fields.Many2one(
        'account.account', string="Doctor's Payable Account",
        domain="[('account_type', '=', 'liability_payable')]",
        help='Only used when the treatment is "Post it as a payable".')

    team_allocation = fields.Selection(
        [('team_first', "The doctor's share is collected first"),
         ('pro_rata', 'Every receipt is split in the same proportion'),
         ('hospital_first', "The hospital's share is collected first")],
        string='Part Payments', default='team_first', required=True,
        help="How a part payment is divided when a patient pays in "
             "instalments.\n"
             "Doctor first: nothing is recognised as hospital money until the "
             "doctor's share has been collected in full. A patient paying "
             "6,750 against an 8,000 doctor's share produces no entry at all.\n"
             "Proportional: every receipt is split in the same ratio as the "
             "bill, so hospital income rises smoothly with collection.\n"
             "Hospital first: the hospital is made whole before the doctor, "
             "leaving the doctor carrying any shortfall.")

    discount_account_id = fields.Many2one(
        'account.account', string='Discount Allowed',
        domain="[('account_type', 'in', ('income', 'income_other', 'expense'))]",
        help='Where a bill or admission discount is posted. Without it the '
             'discount is not recognised at all and its value silently piles up '
             'in Accounts Receivable as a debt nobody will ever pay.')

    def _team_off_ledger(self):
        self.ensure_one()
        return self.team_charge_treatment == 'off_ledger'

    def _team_cumulative_hospital(self, paid, total, team):
        """The hospital's share of everything collected so far.

        Written as a *cumulative* function of the amount collected rather than
        a rule applied per receipt, so the split of any one payment is simply
        the difference between the cumulative figure before and after it. That
        keeps a sequence of part payments adding up exactly to the split of the
        whole bill, whichever policy is in force, and makes an out-of-order or
        corrected payment self-healing.
        """
        self.ensure_one()
        total = max(total or 0.0, 0.0)
        team = min(max(team or 0.0, 0.0), total)
        hospital = total - team
        paid = min(max(paid or 0.0, 0.0), total)   # ignore any overpayment
        if total <= 0:
            return 0.0
        if self.team_allocation == 'team_first':
            # Nothing is the hospital's until the doctor is covered.
            return max(0.0, paid - team)
        if self.team_allocation == 'hospital_first':
            return min(paid, hospital)
        return paid * hospital / total
