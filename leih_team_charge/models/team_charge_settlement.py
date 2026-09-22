from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class TeamChargeSettlement(models.Model):
    """Handing a doctor the share the patient has already paid in.

    The surgeon takes their money from the counter, not from the accounts
    department, so this is a counter document: it moves cash out of the drawer
    and shows up in the cash collection report as a negative line, next to the
    patient money that came in. The drawer at close is simply collections less
    payouts.

    Two entries, always in the same shape whenever the payout happens::

        Dr Patient Advances       Cr Doctor's Payable    the share is earned
        Dr Doctor's Payable       Cr Cash                the cash goes out

    When the admission was released first, the settlement entry already credited
    the payable, so only the second entry is raised here. When the counter pays
    the doctor before release -- which is allowed as soon as the patient's money
    covers it -- both are raised together. Either way a doctor's payable balance
    is exactly what they are owed, and it is readable per doctor because each one
    posts against their own partner record.

    Nothing may be handed over that the patient has not handed in first:
    ``_team_budget`` is the patient's money on that admission less whatever has
    already gone out to doctors on it, which is what stops two surgeons on one
    admission being paid the same money.
    """
    _name = 'team.charge.settlement'
    _description = "Doctor's Share Settlement"
    _order = 'date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(default='New', readonly=True, copy=False)
    doctor_id = fields.Many2one(
        'doctors.profile', string='Doctor', required=True, index=True)
    admission_id = fields.Many2one(
        'hospital.admission', string='Admission', index=True,
        help='Settle one admission. Leave empty to sweep up counter bills and '
             'every admission in the date range instead.')
    date = fields.Date('Paid On', default=fields.Date.context_today, required=True)
    date_from = fields.Date('Charges From')
    date_to = fields.Date('Charges To', default=fields.Date.context_today)
    payment_type = fields.Many2one(
        'payment.type', string='Paid By',
        help='Which counter account the cash leaves. Blank uses the payment '
             "journal's own account.")
    amount = fields.Float('Amount Paid', compute='_compute_amount', store=True)
    charge_count = fields.Integer(compute='_compute_amount', store=True)
    payment_note = fields.Char('Note')
    state = fields.Selection(
        [('draft', 'Draft'), ('done', 'Paid'), ('cancel', 'Cancelled')],
        default='draft', required=True, copy=False, index=True)

    line_ids = fields.One2many(
        'team.charge.settlement.line', 'settlement_id', string='Shares Paid',
        copy=False)
    acc_move_ids = fields.Many2many(
        'account.move', 'team_settlement_acc_move_rel', 'settlement_id', 'move_id',
        string='Journal Entries', copy=False)
    acc_move_count = fields.Integer(compute='_compute_acc_move_count')

    # Kept so the existing screens and reports still resolve; both are simply
    # the carriers behind this settlement's lines.
    admission_charge_ids = fields.One2many(
        'hospital.admission.charge', 'team_settlement_id', string='Ward Charges',
        readonly=True)
    bill_line_ids = fields.One2many(
        'bill.register.line', 'team_settlement_id', string='Counter Charges',
        readonly=True)

    @api.depends('line_ids.amount')
    def _compute_amount(self):
        for rec in self:
            rec.amount = sum(rec.line_ids.mapped('amount'))
            rec.charge_count = len(rec.line_ids)

    @api.depends('acc_move_ids')
    def _compute_acc_move_count(self):
        for rec in self:
            rec.acc_move_count = len(rec.acc_move_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'team.charge.settlement') or 'New'
        return super().create(vals_list)

    def action_view_acc_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entries'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.acc_move_ids.ids)],
        }

    # ------------------------------------------------------------------
    # Gathering
    # ------------------------------------------------------------------
    def _carrier_domain(self, model):
        """Shares of this doctor's that are still owed, in scope."""
        self.ensure_one()
        domain = [('team_provider_id', '=', self.doctor_id.id), ('team_due', '>', 0)]
        if model == 'hospital.admission.charge':
            if self.admission_id:
                return domain + [('admission_id', '=', self.admission_id.id)]
            if self.date_from:
                domain += [('date', '>=', self.date_from)]
            if self.date_to:
                domain += [('date', '<=', self.date_to)]
            return domain
        if self.admission_id:
            # Counter bills raised against that admission.
            return domain + [('bill_register_id.general_admission_id', '=',
                              self.admission_id.id)]
        if self.date_from:
            domain += [('bill_register_id.date', '>=', self.date_from)]
        if self.date_to:
            domain += [('bill_register_id.date', '<=', self.date_to)]
        return domain

    def action_collect(self):
        """Pull in what this doctor is owed, capped by what the patient has paid.

        Allocated document by document: each admission or bill has a budget of
        the patient's money that has not already gone out to a doctor, and the
        oldest charges are covered first. A share the patient has only part paid
        comes in for the part they have paid, and the rest waits for a later
        settlement.
        """
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only a draft settlement can gather charges.'))
        self.line_ids.unlink()

        # Two different models, so a plain recordset union is not available:
        # gathered separately and then ordered by the document they sit on.
        carriers = []
        for model in ('hospital.admission.charge', 'bill.register.line'):
            carriers += list(self.env[model].search(self._carrier_domain(model)))

        # One budget per paying document, so two doctors on one admission cannot
        # both be paid out of the same money.
        budgets, vals_list = {}, []
        for carrier in sorted(carriers, key=lambda c: (c._team_document().id, c.id)):
            doc = carrier._team_document()
            if not doc:
                continue
            key = (doc._name, doc.id)
            if key not in budgets:
                budgets[key] = doc._team_budget()
            take = min(carrier.team_due, budgets[key])
            if take <= 0.005:
                continue
            budgets[key] -= take
            vals_list.append(carrier._team_settlement_line_vals(self.id, take))
        if not vals_list:
            raise UserError(_(
                'Nothing can be paid to %(doctor)s yet: either nothing is owed, '
                'or the patients have not paid in enough to cover it.',
                doctor=self.doctor_id.display_name))
        self.env['team.charge.settlement.line'].create(vals_list)
        return True

    # ------------------------------------------------------------------
    # Paying
    # ------------------------------------------------------------------
    def action_done(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only a draft settlement can be paid.'))
            if not rec.line_ids:
                raise UserError(_('Gather the charges before marking this paid.'))
            rec.line_ids._check_within_budget()
            # Work out what still has to be recognised *before* posting: the
            # entitlement entry is built from it, and the charges are only
            # updated once the entries are safely on the ledger.
            rec.line_ids._stamp_entitlement()
            rec._acc_post_payout()
            rec.line_ids._apply()
            rec.state = 'done'
        return True

    def _acc_post_payout(self):
        """Raise the entitlement, then move the cash out of the counter."""
        self.ensure_one()
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled():
            return self.env['account.move']
        payable = cfg._team_payable_account()
        doctor_partner = cfg._team_doctor_partner(self.doctor_id)
        total = sum(self.line_ids.mapped('amount'))
        if total <= 0.005:
            return self.env['account.move']

        moves = self.env['account.move']
        # 1) Whatever has not been recognised yet becomes a payable now, funded
        #    out of the patient's advance -- their money is what pays the doctor.
        by_patient = {}
        for line in self.line_ids:
            if line.entitled_amount <= 0.005:
                continue
            partner = line._patient_partner()
            if not partner:
                raise UserError(_(
                    '%(doc)s has no patient contact record, so the doctor\'s '
                    'share cannot be recognised against the advance.',
                    doc=line.display_name))
            by_patient[partner] = by_patient.get(partner, 0.0) + line.entitled_amount
        if by_patient:
            if not cfg.advance_account_id:
                raise UserError(_(
                    'No "Patient Advances Account" is configured, so a doctor '
                    'cannot be paid before the admission is settled.'))
            lines = []
            for partner, amount in by_patient.items():
                lines.append((cfg.advance_account_id, amount, 0.0, partner))
            lines.append((payable, 0.0, sum(by_patient.values()), doctor_partner))
            move = cfg._create_move(
                cfg.sales_journal_id,
                _('%(ref)s (share earned)', ref=self.name),
                self.date, lines, partner=doctor_partner)
            if move:
                moves |= move

        # 2) The cash leaves the counter.
        journal, cash_account = cfg._payment_accounts(self.payment_type)
        if not journal or not cash_account:
            raise UserError(_(
                'No counter cash account is configured, so the payout cannot be '
                'posted. Set the Payment Journal under Hospital Accounting.'))
        move = cfg._create_move(
            journal, _('%(ref)s (paid to %(doctor)s)',
                       ref=self.name, doctor=self.doctor_id.display_name),
            self.date,
            [(payable, total, 0.0, doctor_partner),
             (cash_account, 0.0, total, False)],
            partner=doctor_partner)
        if move:
            moves |= move
        if moves:
            self.acc_move_ids = [(4, m.id) for m in moves]
        return moves

    def action_cancel(self):
        """Take the money back: reverse the entries and release the shares."""
        cfg = self.env['leih.accounting.config']._get()
        for rec in self:
            if rec.state == 'cancel':
                continue
            reversals = cfg._reverse(rec.acc_move_ids)
            if reversals:
                rec.acc_move_ids = [(4, m.id) for m in reversals]
            rec.line_ids._unapply()
            rec.state = 'cancel'
        return True

    def action_draft(self):
        self.filtered(lambda r: r.state == 'cancel').write({'state': 'draft'})
        return True

    # ------------------------------------------------------------------
    # Bringing the old scheme's balances onto the ledger
    # ------------------------------------------------------------------
    @api.model
    def action_open_team_payables(self):
        """Recognise doctors' shares earned before any of this was posted.

        Under the old treatment the doctor's portion of a patient's payment was
        kept off the ledger entirely: the cash sat in the drawer and the
        obligation sat in a report, and neither was ever posted. Both halves are
        raised here at once, per doctor::

            Dr Cash                   the money that was collected and never posted
            Cr Doctor's Payable       what that money is owed to the doctor

        Only shares the patient has actually paid for are brought in, and only
        the part not already recognised, so running it twice changes nothing.
        Deliberately a manual action: it moves real balances and the figures
        should be read on the Doctor's Share report first.
        """
        cfg = self.env['leih.accounting.config']._get()
        if not cfg._enabled():
            raise UserError(_('Posting to the general ledger is switched off.'))
        payable = cfg._team_payable_account()
        journal, cash_account = cfg._payment_accounts(False)
        if not journal or not cash_account:
            raise UserError(_('No counter cash account is configured.'))

        by_doctor, carriers = {}, []
        for model in ('hospital.admission.charge', 'bill.register.line'):
            carriers += list(self.env[model].search([
                ('team_provider_id', '!=', False),
                ('team_amount', '>', 0),
            ]))
        to_stamp = []
        for carrier in carriers:
            owed = (carrier.team_amount or 0.0) - (carrier.team_entitled or 0.0)
            collected = carrier._team_collected() - (carrier.team_entitled or 0.0)
            amount = max(min(owed, collected), 0.0)
            if amount <= 0.005:
                continue
            by_doctor[carrier.team_provider_id] = \
                by_doctor.get(carrier.team_provider_id, 0.0) + amount
            to_stamp.append((carrier, amount))
        if not by_doctor:
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _("Doctors' Shares"), 'type': 'warning',
                           'message': _('Nothing to bring in: every share the '
                                        'patients have paid for is already '
                                        'recognised.'), 'sticky': False},
            }

        total = sum(by_doctor.values())
        lines = [(cash_account, total, 0.0, False)]
        for doctor, amount in by_doctor.items():
            lines.append((payable, 0.0, amount, cfg._team_doctor_partner(doctor)))
        move = cfg._create_move(
            journal, _("Doctors' shares earned before posting began"),
            fields.Date.context_today(self), lines)
        if move:
            for carrier, amount in to_stamp:
                carrier.with_context(team_settling=True).team_entitled = \
                    (carrier.team_entitled or 0.0) + amount
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {
                'title': _("Doctors' Shares"), 'type': 'success', 'sticky': False,
                'message': _('%(total)s brought onto the ledger across '
                             '%(doctors)s doctor(s).',
                             total=total, doctors=len(by_doctor)),
            },
        }


class TeamChargeSettlementLine(models.Model):
    """One share, and how much of it this payout hands over.

    A line rather than a stamp on the charge, because a share can be paid in
    instalments: the counter gives the surgeon what the patient's money covers
    today and the rest follows. The charge keeps the running totals; this is the
    record of each movement.
    """
    _name = 'team.charge.settlement.line'
    _description = "Doctor's Share Settlement Line"

    settlement_id = fields.Many2one(
        'team.charge.settlement', required=True, ondelete='cascade', index=True)
    doctor_id = fields.Many2one(related='settlement_id.doctor_id', store=True)
    charge_id = fields.Many2one(
        'hospital.admission.charge', string='Ward Charge', ondelete='cascade', index=True)
    bill_line_id = fields.Many2one(
        'bill.register.line', string='Counter Charge', ondelete='cascade', index=True)
    description = fields.Char(readonly=True)
    owed = fields.Float("Doctor's Share", readonly=True)
    already_paid = fields.Float('Already Paid', readonly=True)
    amount = fields.Float('Paying Now', required=True)
    # How much of `amount` still had to be recognised as a payable when this
    # settlement was made. Stored so cancelling gives back exactly what this
    # document added and not what the release entry had already recognised.
    entitled_amount = fields.Float('Recognised Here', readonly=True)

    def _carrier(self):
        self.ensure_one()
        return self.charge_id or self.bill_line_id

    def _patient_partner(self):
        self.ensure_one()
        doc = self._carrier()._team_document()
        patient = getattr(doc, 'patient_name', False)
        return patient.partner_id if patient else False

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount < 0:
                raise ValidationError(_('A payout cannot be negative.'))
            carrier = rec._carrier()
            if carrier and rec.amount > (carrier.team_due or 0.0) + 0.005:
                raise ValidationError(_(
                    'Paying %(amount)s of %(desc)s, but only %(due)s is still '
                    'owed to the doctor on it.',
                    amount=rec.amount, desc=rec.description or '/',
                    due=carrier.team_due))

    def _check_within_budget(self):
        """No doctor may be handed money the patient has not handed in."""
        budgets = {}
        for rec in self:
            doc = rec._carrier()._team_document()
            key = (doc._name, doc.id)
            if key not in budgets:
                budgets[key] = doc._team_budget()
            budgets[key] -= rec.amount
            if budgets[key] < -0.005:
                raise UserError(_(
                    'This would hand over more than the patient has paid on '
                    '%(doc)s. They have paid in %(budget)s that has not already '
                    'gone to a doctor.',
                    doc=doc.display_name, budget=doc._team_budget()))
        return True

    def _stamp_entitlement(self):
        """How much of each payout still has to be recognised as a payable.

        Zero when the admission was released first -- the settlement entry has
        already credited the doctor -- and the whole amount when the counter is
        paying ahead of release.
        """
        for rec in self:
            carrier = rec._carrier()
            if not carrier or rec.amount <= 0.005:
                rec.entitled_amount = 0.0
                continue
            not_entitled = max((carrier.team_amount or 0.0)
                               - (carrier.team_entitled or 0.0), 0.0)
            rec.entitled_amount = min(rec.amount, not_entitled)
        return True

    def _apply(self):
        """Move the amounts onto the charges the money came from."""
        for rec in self:
            carrier = rec._carrier()
            if not carrier or rec.amount <= 0.005:
                continue
            carrier.with_context(team_settling=True).write({
                'team_paid': (carrier.team_paid or 0.0) + rec.amount,
                'team_entitled': (carrier.team_entitled or 0.0) + rec.entitled_amount,
                'team_settlement_id': rec.settlement_id.id,
            })
        return True

    def _unapply(self):
        for rec in self:
            carrier = rec._carrier()
            if not carrier:
                continue
            carrier.with_context(team_settling=True).write({
                'team_paid': max((carrier.team_paid or 0.0) - rec.amount, 0.0),
                'team_entitled': max((carrier.team_entitled or 0.0)
                                     - rec.entitled_amount, 0.0),
                'team_settlement_id': False,
            })
        return True
