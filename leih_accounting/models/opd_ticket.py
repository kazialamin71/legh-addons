from odoo import _, api, fields, models


class OpdTicket(models.Model):
    """Post an OPD ticket's money to the GL, and reverse it when it is cancelled.

      Ticket:  Dr Cash/Bank (payment type account)   total
               Cr Income (per ticket item account)   total
      Cancel:  the reverse of the above.

    OPD is a counter sale -- the patient pays for the ticket before seeing the
    doctor -- so there is no receivable stage to post: one entry books the income
    and the cash in the same move, on the day the ticket was issued.

    Like every other poster here this is off until an administrator configures
    ``leih.accounting.config`` and turns posting on; a ticket issued before then
    still prints, receipts and collects, it just leaves the ledger alone.
    """
    _inherit = 'opd.ticket'

    acc_move_ids = fields.Many2many(
        'account.move', 'opd_ticket_acc_move_rel', 'ticket_id', 'move_id',
        string='Journal Entries', copy=False)
    acc_posted = fields.Boolean(copy=False)
    acc_move_count = fields.Integer(compute='_compute_acc_move_count')

    @api.depends('acc_move_ids')
    def _compute_acc_move_count(self):
        for rec in self:
            rec.acc_move_count = len(rec.acc_move_ids)

    def action_view_acc_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entries'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.acc_move_ids.ids)],
        }

    # ---------------------------------------------------------------- hooks
    def _settle_ticket_money(self):
        # A ticket is often saved before its items are keyed in, so the amount
        # to post only turns up later; the hook fires on both.
        super()._settle_ticket_money()
        self._acc_post_ticket()

    def action_cancel(self):
        result = super().action_cancel()
        cfg = self.env['leih.accounting.config']._get()
        for ticket in self:
            # Keep the reversals on the ticket: orphaned, they are impossible to
            # trace back from the document whose entries they undo.
            reversals = cfg._reverse(ticket.acc_move_ids)
            if reversals:
                ticket.acc_move_ids = [(4, mv.id) for mv in reversals]
        return result

    # ---------------------------------------------------------------- posting
    def _acc_post_ticket(self):
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled():
            return
        for ticket in self:
            if ticket.acc_posted or ticket.state != 'confirmed':
                continue
            if (ticket.total or 0.0) <= 0:
                continue
            journal, cash_account = cfg._payment_accounts(ticket.payment_type)
            if not journal or not cash_account:
                continue
            # One credit line per income head, so two consultations charged to
            # different departments stay apart in the P&L.
            income = {}
            unaccounted = False
            for line in ticket.opd_ticket_line_id:
                amount = line.total_amount or 0.0
                if not amount:
                    continue
                account = cfg._income_account(line.name)
                if not account:
                    # An item with no account of its own and no default income
                    # account configured would silently swallow part of the
                    # ticket. Leave the whole ticket unposted instead, so it
                    # reads as missing revenue rather than as a wrong entry.
                    unaccounted = True
                    break
                income.setdefault(account, 0.0)
                income[account] += amount
            if unaccounted or not income:
                continue
            total = sum(income.values())
            partner = ticket.patient_name.partner_id
            lines = [(cash_account, total, 0.0, partner)]
            for account, amount in income.items():
                lines.append((account, 0.0, amount, partner))
            move = cfg._create_move(journal, ticket.name, ticket.date, lines, partner=partner)
            if move:
                ticket.acc_move_ids = [(4, move.id)]
                ticket.acc_posted = True
