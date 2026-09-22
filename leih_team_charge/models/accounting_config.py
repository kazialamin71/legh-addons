from odoo import _, fields, models
from odoo.exceptions import UserError


class LeihAccountingConfig(models.Model):
    """Where the doctor's share lives between being earned and being paid out.

    There used to be a choice here -- keep the doctor's share out of the ledger
    entirely, or post it as a payable -- and a policy for splitting every part
    payment between the two. Both are gone, because both were wrong for a
    hospital whose own counter takes the money:

    *Off the ledger* only makes sense when the doctor collects from the patient
    directly. Here the cashier takes the whole amount, so it is the hospital's
    cash and the hospital's obligation; leaving both out understated the balance
    sheet on both sides. Worse, the split was applied at *receipt* time, so under
    "the doctor's share is collected first" a patient paying 5,000 against a
    20,000 doctor's share produced no journal entry at all -- real money in the
    drawer that the ledger had never heard of.

    *Splitting each receipt* was guesswork: it decided whose money had arrived
    before the charges were even final. The share is now settled once, when it is
    actually known, and every receipt simply posts the cash that came in.
    """
    _inherit = 'leih.accounting.config'

    team_payable_account_id = fields.Many2one(
        'account.account', string="Doctor's Payable Account",
        domain="[('account_type', '=', 'liability_payable')]",
        help="Where a doctor's share is held between being earned and being "
             "handed over at the counter. Each doctor's own partner record "
             "carries their balance, so what is owed to whom reads straight off "
             "the partner ledger.")

    discount_account_id = fields.Many2one(
        'account.account', string='Discount Allowed',
        domain="[('account_type', 'in', ('income', 'income_other', 'expense'))]",
        help='Where a bill or admission discount is posted. Without it the '
             'discount is not recognised at all and its value silently piles up '
             'in Accounts Receivable as a debt nobody will ever pay.')

    def _team_payable_account(self):
        """Where a doctor's share is held. Refuses rather than falling back.

        A share posted to some other head is money the hospital believes it owns
        and will never be told otherwise.
        """
        self.ensure_one()
        if not self.team_payable_account_id:
            raise UserError(_(
                'No "Doctor\'s Payable Account" is configured under Accounting > '
                'Configuration > Hospital Accounting, so the doctor\'s share '
                'cannot be recognised. Set one (an account of type "Payable").'))
        return self.team_payable_account_id

    def _team_doctor_partner(self, doctor):
        """The partner a doctor's payable is booked against."""
        self.ensure_one()
        if not doctor.partner_id:
            raise UserError(_(
                '%(doctor)s has no contact record, so their share cannot be '
                'booked to the payable ledger. Set "Partner" on the doctor.',
                doctor=doctor.display_name))
        return doctor.partner_id
