from odoo import api, fields, models


class BillRegister(models.Model):
    """Post revenue at confirm and a payment entry per receipt (off by default).

      Confirm:  Dr Accounts Receivable (patient)   grand_total
                Cr Income (per item account)        grand_total (net, scaled)
      Payment:  Dr Cash/Bank                        amount
                Cr Accounts Receivable (patient)    amount

    **Counter bills only.** A bill raised against an admission
    (``general_admission_id`` set) posts nothing here: the admission recognises
    all of its income once, at final settlement, out of the charge ledger that
    ``calculate_bill`` pulls these very lines into.

    leih_team_charge overrides ``_acc_post_revenue`` and does *not* apply that
    rule -- with team charges kept off the ledger an investigation recognises the
    hospital's share at confirm, and the admission leaves those charges out of
    its settlement entry instead. The receivable that raises is cleared against
    the patient's advance when the admission is released
    (``hospital.admission._acc_settle_investigation_receivables``).

    Posting both would double-count, and it already did. The bill booked
    ``Dr AR / Cr Income`` at confirm while the admission booked its money to
    Patient Advances and then deliberately *excluded* those same charges from the
    release entry -- so the bill's receivable and the admission's advance
    liability both sat open on the balance sheet for ever, pointing at one amount
    the patient had already paid.

    Money taken on an admission bill is an admission advance for the same reason,
    and is posted as one: ``calculate_bill`` folds ``bill.paid`` into the
    admission's ``investigation_paid``, which is what settles the admission.
    """
    _inherit = 'bill.register'

    acc_move_ids = fields.Many2many(
        'account.move', 'bill_register_acc_move_rel', 'bill_id', 'move_id',
        string='Journal Entries', copy=False)
    acc_revenue_posted = fields.Boolean(copy=False)
    acc_move_count = fields.Integer(compute='_compute_acc_move_count')

    @api.depends('acc_move_ids')
    def _compute_acc_move_count(self):
        for rec in self:
            rec.acc_move_count = len(rec.acc_move_ids)

    # ------------------------------------------------------------------ refs
    def _acc_move_ref(self):
        """What this bill's journal entries are referenced by.

        An investigation billed to an admitted patient carries the admission
        number as well. Reading a receivable off the general ledger and having
        no way to tell which admission it belonged to is exactly what made these
        balances impossible to chase.
        """
        self.ensure_one()
        if self.general_admission_id:
            return '%s / %s' % (self.name or '', self.general_admission_id.name or '')
        return self.name

    def _acc_open_receivable(self):
        """How much of this bill is still standing in Accounts Receivable.

        Read off the bill's own posted entries rather than recomputed from the
        figures on the form. With the doctor's share kept off the ledger the
        amount that reached Accounts Receivable is not the bill's grand total,
        and the ledger is the only thing that knows the difference.
        """
        self.ensure_one()
        cfg = self.env['leih.accounting.config']._get()
        partner = self.patient_name.partner_id
        receivable = cfg._receivable_account(partner) if partner else False
        if not receivable:
            return 0.0
        lines = self.acc_move_ids.filtered(
            lambda m: m.state == 'posted').line_ids.filtered(
            lambda l: l.account_id == receivable)
        return max(sum(lines.mapped('debit')) - sum(lines.mapped('credit')), 0.0)

    def action_view_acc_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entries',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.acc_move_ids.ids)],
        }

    # ---------------------------------------------------------------- hooks
    def bill_confirm(self):
        # Revenue first: confirm now also receipts the counter's "Paid Now",
        # and that receipt credits the receivable this entry raises. Posting
        # the other way round leaves the two moves reading backwards on the
        # ledger.
        self._acc_post_revenue()
        return super().bill_confirm()

    def bill_cancel(self):
        res = super().bill_cancel()
        cfg = self.env['leih.accounting.config']._get()
        # Keep the reversals on the bill: orphaned, they are impossible to trace
        # back from the document whose entries they undo.
        reversals = cfg._reverse(self.acc_move_ids)
        if reversals:
            self.acc_move_ids = [(4, mv.id) for mv in reversals]
        return res

    def _register_payment(self, amount, payment_type=None, date=None, card_no=None, bank_name=None):
        mr = super()._register_payment(amount, payment_type=payment_type, date=date,
                                       card_no=card_no, bank_name=bank_name)
        if mr:
            self._acc_post_payment(amount, payment_type or self.payment_type, date)
        return mr

    # ---------------------------------------------------------------- posting
    def _acc_is_admission_borne(self):
        """True when this bill's income belongs to an admission's settlement."""
        self.ensure_one()
        return bool(self.general_admission_id)

    def _acc_payment_is_admission_advance(self):
        """True when money taken on this bill is an advance on the admission.

        Only when the bill genuinely deferred its income. A bill that recognised
        its own revenue also raised its own receivable, and its payment has to
        clear *that* -- posting it to Patient Advances instead leaves a paid bill
        with its receivable still standing and the money sitting in a liability
        account, which is the very gap the release settlement exists to close,
        recreated one bill at a time.

        This is not hypothetical: with team charges kept off the ledger every
        admission-linked investigation recognises its own revenue at confirm, so
        reading ``general_admission_id`` alone sent every counter payment on one
        of those bills to the wrong account -- and where the doctor's share was
        nil and the admission had no charges yet, the slice came out at zero and
        the cash was never posted at all.
        """
        self.ensure_one()
        return self._acc_is_admission_borne() and not self.acc_revenue_posted

    def _acc_post_revenue(self):
        self.ensure_one()
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled() or self.acc_revenue_posted:
            return
        if self._acc_is_admission_borne():
            return
        partner = self.patient_name.partner_id
        receivable = cfg._receivable_account(partner) if partner else False
        if not partner or not receivable:
            return
        line_total = sum(self.bill_register_line_id.mapped('total_amount'))
        grand = self.grand_total or 0.0
        if line_total <= 0 or grand <= 0:
            return
        scale = grand / line_total  # spread bill-level discount into net income
        income = {}
        for line in self.bill_register_line_id:
            acct = cfg._income_account(line.name)
            if not acct:
                continue
            income.setdefault(acct, 0.0)
            income[acct] += (line.total_amount or 0.0) * scale
        if not income:
            return
        lines = [(receivable, grand, 0.0, partner)]
        for acct, amt in income.items():
            lines.append((acct, 0.0, amt, partner))
        move = cfg._create_move(cfg.sales_journal_id, self._acc_move_ref(), self.date,
                                lines, partner=partner)
        if move:
            self.acc_move_ids = [(4, move.id)]
            self.acc_revenue_posted = True

    def _acc_post_payment(self, amount, payment_type, date):
        self.ensure_one()
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled() or amount <= 0:
            return
        # Money on an admission bill that deferred its income is an advance
        # against the admission, not a settlement of a receivable this bill never
        # raised. Book it the way the admission's own payments are booked, so the
        # settlement entry can apply it; otherwise it would credit a receivable
        # with no debit behind it. A bill that did raise its own receivable falls
        # through and clears it below.
        if self._acc_payment_is_admission_advance():
            move = self.general_admission_id._acc_post_advance(
                amount, payment_type, date)
            if move:
                self.acc_move_ids = [(4, move.id)]
            return
        partner = self.patient_name.partner_id
        receivable = cfg._receivable_account(partner) if partner else False
        if not partner or not receivable:
            return
        journal, cash_account = cfg._payment_accounts(payment_type)
        if not journal or not cash_account:
            return
        lines = [
            (cash_account, amount, 0.0, False),
            (receivable, 0.0, amount, partner),
        ]
        move = cfg._create_move(journal, self._acc_move_ref(), date, lines, partner=partner)
        if move:
            self.acc_move_ids = [(4, move.id)]
