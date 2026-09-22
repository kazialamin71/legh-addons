from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .income_heads import HOSPITAL_INCOME_HEADS


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
    discount_account_id = fields.Many2one(
        'account.account', string='Discount Allowed Account',
        domain="[('account_type', 'in', ('income', 'expense', 'expense_direct_cost'))]",
        help='Contra-revenue account debited for discounts given. Revenue is '
             'credited gross and the amount let off is debited here, so the '
             'discount given in a period is reportable from the ledger. Leave '
             'blank to credit revenue net instead, which hides it.')

    # Bed, cabin, ICU, doctor fee and manual medicine charges have no catalogue
    # item behind them -- there is no account field on hospital.bed or
    # doctors.profile to read -- so without this they would all collapse into the
    # default income account. One row per service type is the smallest thing that
    # keeps ward income, doctor fees and pharmacy apart in the P&L, and it lives
    # here rather than on five legacy models.
    income_map_ids = fields.One2many(
        'leih.accounting.income.map', 'config_id', string='Income by Service Type')

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
        """Item account first, then default. Kept for bill.register, which bills
        examination.entry items and nothing else."""
        self.ensure_one()
        if entry and entry.accounts_id:
            return entry.accounts_id
        return self.default_income_account_id

    def _service_type_account(self, service_type):
        """The configured account for a charge's service type, if mapped."""
        self.ensure_one()
        row = self.income_map_ids.filtered(lambda r: r.service_type == service_type)[:1]
        return row.account_id if row else self.env['account.account']

    def _charge_income_account(self, charge):
        """Which account a charge ledger row credits.

        Four steps, most specific first:

        1. ``charge.income_account_id`` -- seeded from the catalogue item
           (``examination.entry.accounts_id`` for diagnostics,
           ``admission.charge.item.accounts_id`` for ward charges) when the
           ledger is rebuilt, and overridable by hand on the line.
        2. what the charge is *for*: the bed (bed > ward > category) or the
           doctor. Read live rather than only at stamping time, so configuring
           an ICU category account this afternoon fixes tonight's release
           without anyone remembering to press Calculate Payable first.
        3. the service-type map -- the fallback for every bed, cabin, ICU, NICU,
           HDU, doctor fee and pharmacy charge that has been configured no more
           finely than its type.
        4. the default income account.

        Returning an empty recordset is not a silent skip: the poster refuses to
        post a charge it cannot account for, rather than quietly dropping the
        revenue.
        """
        self.ensure_one()
        return (charge.income_account_id
                or charge._source_income_account()
                or self._service_type_account(charge.service_type)
                or self.default_income_account_id
                or self.env['account.account'])

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

    # ------------------------------------------------------- income heads
    @api.model
    def _is_rollup(self, account):
        """True for an account that only exists to add its children up.

        ``parent_id`` comes from account_parent_hierarchy, which may not be
        installed; without it no account is ever a roll-up and everything below
        is a no-op rather than a crash.
        """
        Account = self.env['account.account']
        if 'parent_id' not in Account._fields or not account:
            return False
        return bool(Account.search_count([('parent_id', '=', account.id)], limit=1))

    def action_setup_income_heads(self):
        """Build the hospital income chart and map every service type onto it.

        Idempotent, and deliberately conservative about a chart that is already
        in use: accounts are matched **by code**, only missing ones are created,
        an existing name is never overwritten, and a parent is only filled in
        where nobody has chosen one. Service-type rows are only added where the
        type is not already mapped -- a mapping the accountant changed by hand
        survives a re-run.
        """
        self.ensure_one()
        Account = self.env['account.account'].with_company(self.company_id)
        supports_parent = 'parent_id' in Account._fields
        created = self.env['account.account']

        # Pass 1 -- every head exists.
        by_code = {}
        for code, name, _parent, _stype in HOSPITAL_INCOME_HEADS:
            account = Account.search([('code', '=', code)], limit=1)
            if not account:
                account = Account.create({
                    'code': code,
                    'name': name,
                    'account_type': 'income',
                    'company_ids': [(6, 0, self.company_id.ids)],
                })
                created |= account
            by_code[code] = account

        # Pass 2 -- parents, once every account has an id to point at.
        if supports_parent:
            for code, _name, parent, _stype in HOSPITAL_INCOME_HEADS:
                account, parent_account = by_code[code], by_code.get(parent)
                if parent_account and not account.parent_id and account != parent_account:
                    account.parent_id = parent_account

        # Pass 3 -- the service-type map, leaving hand-made choices alone.
        Map = self.env['leih.accounting.income.map']
        mapped = set(self.income_map_ids.mapped('service_type'))
        rows = 0
        for code, _name, _parent, stype in HOSPITAL_INCOME_HEADS:
            if not stype or stype in mapped:
                continue
            Map.create({
                'config_id': self.id,
                'service_type': stype,
                'account_id': by_code[code].id,
            })
            mapped.add(stype)
            rows += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _('Income heads ready'),
                'message': _(
                    '%(created)s account(s) created, %(rows)s service type(s) mapped. '
                    'Existing accounts, names and mappings were left untouched.',
                    created=len(created), rows=rows),
                'sticky': False,
            },
        }

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
        rollups = [a for a, d, c, _p in lines if (d or c) and self._is_rollup(a)]
        if rollups:
            # A parent head is the sum of its children. Posting straight to it
            # double-counts in the hierarchy report and there is no way to tell
            # afterwards which child the money belonged to.
            raise UserError(_(
                'These are roll-up (parent) accounts and cannot be posted to '
                'directly. Point the charge or the service-type map at one of '
                'their child accounts instead:\n\n%(rows)s',
                rows='\n'.join('  - %s' % a.display_name for a in rollups)))
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
        """Reverse posted moves and hand the reversals back, so the caller can
        keep them on the record they belong to instead of orphaning them.

        One defaults dict **per move**: ``_reverse_moves`` zips the two together,
        so a single-element list silently reversed only the first move and left
        every other entry on the document standing. Cancelling anything with
        more than one entry behind it -- a payout, an admission, a bill with a
        payment -- left half of it on the ledger.
        """
        moves = moves.filtered(lambda m: m.state == 'posted')
        if not moves:
            return self.env['account.move']
        today = fields.Date.context_today(self)
        return moves._reverse_moves([{'date': today}] * len(moves), cancel=True)


class LeihAccountingIncomeMap(models.Model):
    """Income account per charge service type.

    The fallback for every charge whose catalogue item carries no account -- and
    for bed, cabin, ICU, NICU, HDU, doctor fee and pharmacy that is *all* of
    them, because no account field exists on hospital.bed or doctors.profile.
    One row each keeps them apart in the P&L without a schema change to the
    legacy ward models.
    """
    _name = 'leih.accounting.income.map'
    _description = 'Hospital Income Account by Service Type'
    _order = 'service_type'

    config_id = fields.Many2one(
        'leih.accounting.config', required=True, ondelete='cascade', index=True)
    service_type = fields.Selection(
        selection=lambda self: self.env['hospital.admission.charge']._fields['service_type'].selection,
        string='Service Type', required=True)
    account_id = fields.Many2one(
        'account.account', string='Income Account', required=True,
        domain="[('account_type', '=', 'income')]")

    _service_type_uniq = models.Constraint(
        'unique (config_id, service_type)',
        'There is already an income account mapped for this service type.',
    )

    @api.constrains('account_id')
    def _check_account_not_rollup(self):
        for rec in self:
            if rec.config_id._is_rollup(rec.account_id):
                raise ValidationError(_(
                    '%(account)s is a roll-up head with child accounts under it. '
                    'Map the service type to one of its children, otherwise the '
                    'hierarchy report counts the same income twice.',
                    account=rec.account_id.display_name))
