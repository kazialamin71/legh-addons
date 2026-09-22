from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HospitalAdmission(models.Model):
    """Admission accounting (off by default).

    The admission is the single invoice. Every service the patient received --
    ward charges, bed/ICU days, doctor visits, pharmacy, *and* the diagnostics
    billed through bill.register -- lands in one charge ledger, and that ledger is
    recognised once, at final settlement::

        Advance payment:  Dr Cash/Bank              amount
                          Cr Patient Advances        amount   (partner = patient)

        Final settlement: Cr Income (per charge)     gross
                          Dr Discount Allowed        discount given
                          Dr Patient Advances        advances applied
                          Dr Accounts Receivable     whatever is still due

    Two deliberate choices, both of which the earlier version got wrong:

    *Gross, not net.* Revenue is credited at the full rate and the amount let off
    is debited to a contra-revenue account. Netting it away made "how much
    discount did we give in March" unanswerable from the ledger, which is the one
    question management actually asks about discounts.

    *All charges, not some.* Diagnostics used to be excluded here on the grounds
    that bill.register recognised its own income -- but the bill booked a
    receivable while the admission booked the patient's money to Patient
    Advances, so neither ever cleared. An admission-linked bill posts nothing
    at confirm (see leih_accounting/models/bill_register.py) and its income is
    recognised here with everything else.

    *Except* when team charges are kept off the ledger: leih_team_charge posts
    the hospital's share of an investigation at confirm and deliberately leaves
    ``hospital.bill.line`` charges out of the settlement entry, so there the
    diagnostic receivable is real. Release clears it against the advance::

        Investigations:   Dr Patient Advances      left in receivables
                          Cr Accounts Receivable   the same

    which is what ``_acc_settle_investigation_receivables`` exists for. It runs
    either way and is a no-op when nothing is outstanding.
    """
    _inherit = 'hospital.admission'

    acc_move_ids = fields.Many2many(
        'account.move', 'hospital_admission_acc_move_rel', 'admission_id', 'move_id',
        string='Journal Entries', copy=False)
    acc_revenue_posted = fields.Boolean(copy=False)
    acc_investigation_settled = fields.Boolean(
        copy=False,
        help="The receivables this admission's investigation bills raised have "
             "been cleared against the patient's advance.")
    acc_move_count = fields.Integer(compute='_compute_acc_move_count')

    @api.depends('acc_move_ids')
    def _compute_acc_move_count(self):
        for rec in self:
            rec.acc_move_count = len(rec.acc_move_ids)

    def action_view_acc_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entries',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.acc_move_ids.ids)],
        }

    def action_acc_repost_revenue(self):
        """Reverse the settlement entry and post it again from the charges.

        The entry is only as good as the income heads that were configured when
        Release was pressed. Fix the heads afterwards -- map a service type, put
        an account on the ICU beds -- and this rebuilds the entry rather than
        leaving the ledger describing a configuration that no longer exists. The
        original is reversed, never deleted, so the audit trail survives.

        Advance receipts are untouched: they were right the first time and the
        patient's money has not moved.
        """
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled():
            raise UserError(_('Posting to the general ledger is switched off.'))
        for rec in self:
            if rec.state != 'released':
                raise UserError(_(
                    'Admission %s is not released, so there is no settlement '
                    'entry to re-post.', rec.name or ''))
            revenue = rec.acc_move_ids.filtered(
                lambda m: m.journal_id == cfg.sales_journal_id)
            reversals = cfg._reverse(revenue)
            if reversals:
                rec.acc_move_ids = [(4, m.id) for m in reversals]
            rec.acc_revenue_posted = False
            # The reversal above swept up the investigation clearing entry as
            # well -- same journal -- so it has to be raised again from the
            # rebuilt position, not left reversed.
            rec.acc_investigation_settled = False
            rec._acc_post_release()
            rec._acc_settle_investigation_receivables()
        return True

    # ---------------------------------------------------------------- hooks
    def _register_admission_payment(self, amount, payment_type=None, date=None, account_number=None):
        mr = super()._register_admission_payment(
            amount, payment_type=payment_type, date=date, account_number=account_number)
        if mr:
            self._acc_post_advance(amount, payment_type or self.payment_type, date)
        return mr

    def btn_final_settlement(self):
        res = super().btn_final_settlement()
        for rec in self.filtered(lambda r: r.state == 'released'):
            rec._acc_post_release()
            # After the settlement entry, so the advance it applies is already
            # off the books and only what is genuinely spare clears the bills.
            rec._acc_settle_investigation_receivables()
        return res

    def admission_cancel(self):
        # Reverse before super(): the base method deletes journal entries whose
        # ref matches the admission name, and a posted entry must be reversed,
        # not deleted. leih19's admission_cancel now leaves posted moves alone
        # for exactly this reason, so the two halves have to happen in this order.
        cfg = self.env['leih.accounting.config']._get()
        for rec in self:
            cfg._reverse(rec.acc_move_ids)
            rec.acc_revenue_posted = False
            rec.acc_investigation_settled = False
        return super().admission_cancel()

    # ---------------------------------------------------------------- posting
    def _acc_post_advance(self, amount, payment_type, date):
        """Money in, before the bill is recognised: a liability, not revenue.

        Returns the move so bill.register can attach it to an admission-linked
        investigation bill, whose payments are advances against this admission.
        """
        self.ensure_one()
        Move = self.env['account.move']
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled() or amount <= 0:
            return Move
        partner = self.patient_name.partner_id
        if not partner or not cfg.advance_account_id:
            return Move
        journal, cash_account = cfg._payment_accounts(payment_type)
        if not journal or not cash_account:
            return Move
        lines = [
            (cash_account, amount, 0.0, False),
            (cfg.advance_account_id, 0.0, amount, partner),
        ]
        move = cfg._create_move(journal, self.name, date, lines, partner=partner)
        if move:
            self.acc_move_ids = [(4, move.id)]
        return move

    def _acc_open_advance(self):
        """How much of this admission's advance is still unapplied, per the ledger.

        Read off the posted entries rather than from ``paid``: advances are
        banked net of the doctor's share when team charges are kept off the
        ledger, so what the account actually holds is not what the form says was
        collected.
        """
        self.ensure_one()
        cfg = self.env['leih.accounting.config']._get()
        if not cfg.advance_account_id:
            return 0.0
        lines = self.acc_move_ids.filtered(
            lambda m: m.state == 'posted').line_ids.filtered(
            lambda l: l.account_id == cfg.advance_account_id)
        return max(sum(lines.mapped('credit')) - sum(lines.mapped('debit')), 0.0)

    def _acc_settle_investigation_receivables(self):
        """Clear the receivables this admission's investigation bills raised.

        An investigation billed to an admitted patient recognises its income and
        debits Accounts Receivable as soon as it is confirmed. The patient never
        settles that bill at the counter, though -- they pay the *admission*, and
        that money is credited to Patient Advances. Nothing ever brought the two
        together, so every released admission left a receivable and an advance of
        the same size standing open against the same patient::

            Dr Patient Advances      what the investigation bills left in AR
            Cr Accounts Receivable   the same

        Capped at the advance actually left unapplied. A patient who genuinely
        still owes money keeps their receivable rather than having a liability
        account pushed into debit to make the gap disappear.
        """
        self.ensure_one()
        Move = self.env['account.move']
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled() or self.acc_investigation_settled:
            return Move
        if not cfg.advance_account_id:
            return Move
        partner = self.patient_name.partner_id
        receivable = cfg._receivable_account(partner) if partner else False
        if not partner or not receivable:
            return Move

        # One entry per bill. A single pooled entry would land in the journal
        # list of every bill it touched -- including bills it did not actually
        # clear once the cap bit -- and reading it back per bill afterwards would
        # subtract the whole pooled amount from each of them.
        bills = self.investigation_bill_ids.filtered(lambda b: b.state == 'confirmed')
        remaining = self._acc_open_advance()
        moves = Move
        outstanding = 0.0
        for bill in bills.sorted('id'):
            open_ar = bill._acc_open_receivable()
            if open_ar <= 0.005:
                continue
            amount = min(open_ar, remaining)
            if amount <= 0.005:
                # The advance is spent. What is left really is owed, so it stays
                # in receivables rather than being papered over.
                outstanding += open_ar
                continue
            lines = [
                (cfg.advance_account_id, amount, 0.0, partner),
                (receivable, 0.0, amount, partner),
            ]
            move = cfg._create_move(
                cfg.sales_journal_id,
                _('%(bill)s / %(adm)s (investigation settlement)',
                  bill=bill.name or '', adm=self.name or ''),
                fields.Date.context_today(self), lines, partner=partner)
            if not move:
                continue
            remaining -= amount
            outstanding += open_ar - amount
            moves |= move
            self.acc_move_ids = [(4, move.id)]
            # On the bill too: this is the entry that cleared its receivable,
            # and it is unfindable from the bill otherwise.
            bill.acc_move_ids = [(4, move.id)]
        if moves and outstanding <= 0.005:
            # Only once nothing is left open, so a clearing cut short by the cap
            # can be finished later rather than being marked done.
            self.acc_investigation_settled = True
        return moves

    @api.model
    def action_clear_investigation_receivables(self):
        """Close the investigation gap on admissions released before this existed.

        Idempotent and capped, exactly as at release: an admission whose bills
        raised no receivable, or whose advance is already spent, is left alone.
        """
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled():
            raise UserError(_('Posting to the general ledger is switched off.'))
        pending = self.search([
            ('state', '=', 'released'),
            ('acc_investigation_settled', '=', False),
        ])
        cleared = self.browse()
        for admission in pending:
            # Bring the bill counter up to date too: these admissions were
            # released before either half of this existed.
            admission._settle_investigation_bills()
            if admission._acc_settle_investigation_receivables():
                cleared |= admission
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Investigation Receivables'),
                'message': _('%(done)s of %(total)s released admission(s) cleared '
                             'against the patient advance.',
                             done=len(cleared), total=len(pending)),
                'type': 'success' if cleared else 'warning',
                'sticky': False,
            },
        }

    def _acc_income_by_account(self, cfg):
        """Charge ledger -> {account: gross amount}, plus the unaccountable rows.

        Gross, because the discount is posted separately. Returns the mapping and
        the charges no account could be found for, so the caller can refuse
        rather than silently drop the revenue.
        """
        self.ensure_one()
        income = {}
        unaccounted = self.env['hospital.admission.charge']
        for charge in self.charge_ids:
            gross = charge.gross_amount or 0.0
            if not gross:
                continue
            account = cfg._charge_income_account(charge)
            if not account:
                unaccounted |= charge
                continue
            income.setdefault(account, 0.0)
            income[account] += gross
        return income, unaccounted

    def _acc_post_release(self):
        self.ensure_one()
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled() or self.acc_revenue_posted:
            return
        partner = self.patient_name.partner_id
        if not partner:
            return
        receivable = cfg._receivable_account(partner)

        income, unaccounted = self._acc_income_by_account(cfg)
        if unaccounted:
            # Refusing is the whole point. Posting what we can would hide the
            # shortfall inside a balanced-looking entry that quietly understates
            # revenue, and nobody would look at it again.
            raise UserError(_(
                'These charges have no income account, so admission %(name)s '
                'cannot be posted to the general ledger:\n\n%(rows)s\n\n'
                'Set an account on the catalogue item, or map the service type '
                'under Accounting > Configuration > Hospital Accounting, or set '
                'a Default Income Account there.',
                name=self.name or '',
                rows='\n'.join(
                    '  - %s (%s)' % (c.description or '/',
                                     dict(c._fields['service_type'].selection).get(c.service_type))
                    for c in unaccounted),
            ))
        gross = sum(income.values())
        if gross <= 0:
            return

        discount = (self.after_discount or 0.0)
        # Never post a discount we cannot name an account for: it would have to
        # come out of revenue instead, which is the netting this design exists to
        # avoid, and the entry would silently stop matching the statement.
        if discount > 0 and not cfg.discount_account_id:
            raise UserError(_(
                'Admission %(name)s gives a discount of %(discount).2f but no '
                '"Discount Allowed Account" is configured under Accounting > '
                'Configuration > Hospital Accounting. Set one so the discount is '
                'posted as a contra-revenue debit rather than hidden inside net '
                'revenue.',
                name=self.name or '', discount=discount))

        net = gross - discount
        # Advances include money taken on admission-linked investigation bills:
        # those bills post their receipts to Patient Advances too, and
        # calculate_bill folds them into investigation_paid.
        advances = (self.paid or 0.0) + (self.investigation_paid or 0.0)
        applied_advance = min(advances, net) if cfg.advance_account_id else 0.0
        ar_amount = net - applied_advance

        lines = []
        for account, amount in income.items():
            lines.append((account, 0.0, amount, partner))
        if discount > 0:
            lines.append((cfg.discount_account_id, discount, 0.0, partner))
        if applied_advance > 0:
            lines.append((cfg.advance_account_id, applied_advance, 0.0, partner))
        if ar_amount > 0.005:
            if not receivable:
                raise UserError(_(
                    'Admission %(name)s still has %(due).2f outstanding and no '
                    'receivable account is configured for the patient.',
                    name=self.name or '', due=ar_amount))
            lines.append((receivable, ar_amount, 0.0, partner))

        move = cfg._create_move(cfg.sales_journal_id, self.name,
                                fields.Date.context_today(self), lines, partner=partner)
        if move:
            self.acc_move_ids = [(4, move.id)]
            self.acc_revenue_posted = True
