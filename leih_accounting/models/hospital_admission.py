from odoo import api, fields, models


class HospitalAdmission(models.Model):
    """Admission accounting (off by default):

      Advance payment:  Dr Cash/Bank            amount
                        Cr Patient Advances      amount   (liability, partner=patient)
      Release (full):   Cr Income (per service)  native_total
                        Dr Patient Advances      min(advances, native_total)
                        Dr Accounts Receivable   remainder (the due, if any)

    Diagnostics billed through bill.register (source 'hospital.bill.line') are
    excluded here -- those bills recognise their own income.
    """
    _inherit = 'hospital.admission'

    acc_move_ids = fields.Many2many(
        'account.move', 'hospital_admission_acc_move_rel', 'admission_id', 'move_id',
        string='Journal Entries', copy=False)
    acc_revenue_posted = fields.Boolean(copy=False)
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
        return res

    def admission_cancel(self):
        res = super().admission_cancel()
        cfg = self.env['leih.accounting.config']._get()
        for rec in self:
            cfg._reverse(rec.acc_move_ids)
        return res

    # ---------------------------------------------------------------- posting
    def _acc_post_advance(self, amount, payment_type, date):
        self.ensure_one()
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled() or amount <= 0:
            return
        partner = self.patient_name.partner_id
        if not partner or not cfg.advance_account_id:
            return
        journal, cash_account = cfg._payment_accounts(payment_type)
        if not journal or not cash_account:
            return
        lines = [
            (cash_account, amount, 0.0, False),
            (cfg.advance_account_id, 0.0, amount, partner),
        ]
        move = cfg._create_move(journal, self.name, date, lines, partner=partner)
        if move:
            self.acc_move_ids = [(4, move.id)]

    def _acc_post_release(self):
        self.ensure_one()
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled() or self.acc_revenue_posted:
            return
        partner = self.patient_name.partner_id
        receivable = cfg._receivable_account(partner) if partner else False
        if not partner:
            return

        # native income = charges NOT already invoiced via bill.register
        native = self.charge_ids.filtered(lambda c: c.source_model != 'hospital.bill.line')
        income = {}
        for charge in native:
            acct = cfg._income_account(charge.item_id) or cfg.default_income_account_id
            if not acct:
                continue
            income.setdefault(acct, 0.0)
            income[acct] += (charge.total_amount or 0.0)
        native_total = sum(income.values())
        if native_total <= 0:
            return

        applied_advance = min(self.paid or 0.0, native_total) if cfg.advance_account_id else 0.0
        ar_amount = native_total - applied_advance

        lines = []
        for acct, amt in income.items():
            lines.append((acct, 0.0, amt, partner))
        if applied_advance > 0:
            lines.append((cfg.advance_account_id, applied_advance, 0.0, partner))
        if ar_amount > 0 and receivable:
            lines.append((receivable, ar_amount, 0.0, partner))
        move = cfg._create_move(cfg.sales_journal_id, self.name, fields.Date.context_today(self),
                                lines, partner=partner)
        if move:
            self.acc_move_ids = [(4, move.id)]
            self.acc_revenue_posted = True
