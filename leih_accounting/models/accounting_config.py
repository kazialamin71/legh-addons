from odoo import api, fields, models


class LeihAccountingConfig(models.Model):
    """Hospital accounting configuration + the posting engine.

    Posting is OFF by default: every poster early-returns until an administrator
    sets the journals/accounts and turns ``posting_enabled`` on. Entries are
    plain journal entries (account.move type 'entry'); the patient is the
    partner on the receivable / advance line so AR & partner-ledger reports work.
    """
    _name = 'leih.accounting.config'
    _description = 'Hospital Accounting Configuration'

    name = fields.Char(default='Hospital Accounting Settings')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company, required=True)
    posting_enabled = fields.Boolean('Post to General Ledger', default=False)

    sales_journal_id = fields.Many2one(
        'account.journal', string='Revenue Journal',
        domain="[('type', 'in', ('sale', 'general'))]")
    payment_journal_id = fields.Many2one(
        'account.journal', string='Payment Journal',
        domain="[('type', 'in', ('cash', 'bank'))]")

    default_income_account_id = fields.Many2one(
        'account.account', string='Default Income Account',
        domain="[('account_type', '=', 'income')]")
    receivable_account_id = fields.Many2one(
        'account.account', string='Receivable Account',
        domain="[('account_type', '=', 'asset_receivable')]",
        help='Fallback if a patient/partner has no receivable property set.')
    advance_account_id = fields.Many2one(
        'account.account', string='Patient Advances Account',
        domain="[('account_type', '=', 'liability_current')]",
        help='Liability account for admission advance deposits (booked on receipt, '
             'cleared at release).')

    # ------------------------------------------------------------------ access
    @api.model
    def _get(self):
        # sudo: posting is triggered by billing/admission users who need not have
        # accounting rights; the engine runs the GL writes elevated.
        cfg = self.sudo().search([('company_id', '=', self.env.company.id)], limit=1)
        if not cfg:
            cfg = self.sudo().create({'company_id': self.env.company.id})
        return cfg

    def _enabled(self):
        self.ensure_one()
        return bool(self.posting_enabled and self.sales_journal_id and self.payment_journal_id)

    # ------------------------------------------------------------ resolution
    def _income_account(self, entry):
        """Item account first, then (future) department, then default."""
        self.ensure_one()
        if entry and entry.accounts_id:
            return entry.accounts_id
        return self.default_income_account_id

    def _receivable_account(self, partner):
        self.ensure_one()
        return partner.property_account_receivable_id or self.receivable_account_id

    def _payment_accounts(self, payment_type):
        """(journal, cash/bank account) for a payment."""
        self.ensure_one()
        journal = self.payment_journal_id
        account = (payment_type.account if payment_type and payment_type.account
                   else journal.default_account_id)
        return journal, account

    # ------------------------------------------------------------ engine
    def _create_move(self, journal, ref, date, lines, partner=False):
        """lines = [(account, debit, credit, line_partner), ...]"""
        self.ensure_one()
        move_lines = []
        for account, debit, credit, line_partner in lines:
            if not account or (not debit and not credit):
                continue
            move_lines.append((0, 0, {
                'account_id': account.id,
                'partner_id': line_partner.id if line_partner else False,
                'name': ref or '/',
                'debit': debit or 0.0,
                'credit': credit or 0.0,
            }))
        if not move_lines:
            return self.env['account.move']
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': date or fields.Date.context_today(self),
            'ref': ref,
            'partner_id': partner.id if partner else False,
            'line_ids': move_lines,
        })
        move.action_post()
        return move

    def _reverse(self, moves):
        moves = moves.filtered(lambda m: m.state == 'posted')
        if moves:
            moves._reverse_moves([{'date': fields.Date.context_today(self)}], cancel=True)
