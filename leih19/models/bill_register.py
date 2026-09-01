# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, timedelta
import logging
_logger = logging.getLogger(__name__)


class BillRegister(models.Model):
    _name = "bill.register"
    _description = "Bill Register"
    _order = "id desc"

    # -----------------------
    # Basic info
    # -----------------------
    name = fields.Char("Bill No", default="New", readonly=True, copy=False)

    mobile = fields.Char(string="Mobile", readonly=True)
    patient_name = fields.Many2one('patient.info', string="Patient Name", required=True)
    patient_id = fields.Char(related='patient_name.patient_id', string="Patient Id", readonly=True)

    address = fields.Char("Address", readonly=True)
    age = fields.Char("Age", readonly=True)
    sex = fields.Char("Sex", readonly=True)

    diagonostic_bill = fields.Boolean("Diagonstic Bill", default=False)
    ref_doctors = fields.Many2one('doctors.profile', string='Referred by')
    referral = fields.Many2one('brokers.info', string='Referral')

    # -----------------------
    # Lines
    # -----------------------
    bill_register_line_id = fields.One2many(
        'bill.register.line', 'bill_register_id', string='Item Entry', required=True
    )
    bill_register_payment_line_id = fields.One2many(
        "bill.register.payment.line", "bill_register_payment_line_id", string="Bill Register Payment"
    )
    bill_journal_relation_id = fields.One2many(
        "bill.journal.relation", "bill_journal_relation_id", string="Journal"
    )

    # -----------------------
    # Totals / discounts
    # -----------------------
    doctors_discounts = fields.Float("Doctor Discount(%)")
    doctor_discount_amt = fields.Float("Doctor Discount Amount", compute="_compute_totals", store=True)
    other_discount = fields.Float("Other Discount (Goodwill)")
    after_discount = fields.Float("Discount Amount", compute="_compute_totals", store=True)
    scheme_discount_total = fields.Float("Scheme Discount", compute="_compute_totals", store=True)

    corporate_client_id = fields.Many2one(
        'discount.configuration', string='Corporate Client',
        help="Corporate / insurance client whose contracted discount auto-applies to matching bill lines.")

    total_without_discount = fields.Float(string="Total without discount", compute="_compute_totals", store=True)
    total = fields.Float(string="Total", compute="_compute_totals", store=True)
    grand_total = fields.Float("Grand Total", compute="_compute_totals", store=True)

    # -----------------------
    # Payment
    # -----------------------
    paid = fields.Float(string="Paid", compute="_compute_paid", store=True,
                        help="Total confirmed payments. Sum of all payment lines / money receipts.")
    down_payment = fields.Float(
        "Paid Now",
        help="Amount collected at the counter when the bill is first saved. "
             "Generates the first money receipt automatically. Later payments use the Pay button.")
    due = fields.Float("Due", compute="_compute_totals", store=True)

    card_no = fields.Char('Card No.')
    bank_name = fields.Char('Bank Name')

    payment_type = fields.Many2one(
        "payment.type", string="Payment Type",
        default=lambda self: self.env['payment.type'].search([('name', '=', 'Cash')], limit=1)
    )
    # Drives the card / bank / account fields in the form: cash collects none of
    # them, every other payment type does.
    payment_is_cash = fields.Boolean(related='payment_type.is_cash', string="Cash Payment")
    service_charge = fields.Float("Service Charge", compute="_compute_service_charge", store=True)
    to_be_paid = fields.Float("To be Paid", compute="_compute_service_charge", store=True)
    account_number = fields.Char("Account Number")

    discount_remarks = fields.Char("Discount Remarks")

    # -----------------------
    # Meta
    # -----------------------
    date = fields.Datetime("Date", readonly=True, default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='Assigned to', default=lambda self: self.env.user, tracking=True)

    state = fields.Selection(
        [('pending', 'Pending'), ('confirmed', 'Confirmed'), ('released', 'Released'), ('cancelled', 'Cancelled')],
        string='Status', default='pending', readonly=True
    )

    old_journal = fields.Boolean("Old Journal")
    general_admission_id = fields.Many2one(
        "hospital.admission",
        string="General Admission ID",
    )
    is_applied_to_admission = fields.Boolean(string="Is applied",default=False)

    # ---- Lab integration ----
    specimen_ids = fields.One2many('lab.specimen', 'bill_register_id', string='Lab Specimens')
    lab_result_ids = fields.One2many('examination.result', 'bill_register_id', string='Lab Results')
    specimen_count = fields.Integer(compute='_compute_lab_counts')
    lab_result_count = fields.Integer(compute='_compute_lab_counts')

    @api.depends('specimen_ids', 'lab_result_ids')
    def _compute_lab_counts(self):
        for rec in self:
            rec.specimen_count = len(rec.specimen_ids)
            rec.lab_result_count = len(rec.lab_result_ids)


    @api.onchange("general_admission_id")
    def _onchange_general_admission_id(self):
        for record in self:
            record.patient_name = record.general_admission_id.patient_name or False

    @api.onchange("patient_name")
    def _onchange_patient_name(self):
        """Fill patient details when a patient is selected or created inline."""
        for rec in self:
            patient = rec.patient_name
            rec.mobile = patient.mobile or False
            rec.address = patient.address or False
            rec.age = patient.age or False
            rec.sex = patient.sex or False

    def _desired_support_qty(self, main_lines):
        """Return {support_entry_id: total_qty} required by the given main lines.

        Every main line that carries an active supporting item contributes that
        item's configured quantity; items shared by several main tests (e.g. one
        Test Tube for both CBC and RBS) are summed into a single quantity."""
        desired = {}
        for line in main_lines:
            if line.is_support_line or not line.name:
                continue
            for sup in line.name.support_item_ids:
                if not sup.is_active or not sup.support_entry_id:
                    continue
                sid = sup.support_entry_id.id
                desired[sid] = desired.get(sid, 0.0) + (sup.quantity or 1.0)
        return desired

    @api.onchange('bill_register_line_id')
    def _onchange_add_support_items(self):
        """Live UX: keep exactly one supporting line per supporting item, with its
        quantity summed across every main test that needs it. Adding a main item
        bumps the quantity (or adds the line); removing one lowers it (or removes
        the line). The server-side reconcile guarantees the same on save."""
        Line = self.env['bill.register.line']
        for rec in self:
            lines = rec.bill_register_line_id
            desired = rec._desired_support_qty(lines.filtered(lambda l: not l.is_support_line))
            seen = set()
            for sl in lines.filtered(lambda l: l.is_support_line):
                sid = sl.name.id
                if sid in desired and sid not in seen:
                    if sl.product_qty != desired[sid]:
                        sl.product_qty = desired[sid]
                    seen.add(sid)
                else:
                    # no longer needed, or a duplicate of one already kept
                    rec.bill_register_line_id -= sl
            for sid, qty in desired.items():
                if sid in seen:
                    continue
                sup_entry = self.env['examination.entry'].browse(sid)
                vals = Line._prepare_exam_values(sup_entry)
                vals.update({'name': sid, 'product_qty': qty, 'is_support_line': True})
                rec.bill_register_line_id |= Line.new(vals)

    # -------------------------------------------------------------------------
    # COMPUTES
    # -------------------------------------------------------------------------
    @api.depends(
        'bill_register_line_id',
        'bill_register_line_id.price',
        'bill_register_line_id.product_qty',
        'bill_register_line_id.total_amount',
        'bill_register_line_id.total_discount',
        'bill_register_line_id.scheme_discount_amt',
        'doctors_discounts',
        'other_discount',
        'paid',
    )
    def _compute_totals(self):
        """
        Always keep totals correct (UI + backend).

        Discount order of operations (per line, then bill level):
          list = price x qty
            -> manual line discount (% then flat)
            -> scheme discount (auto %, corporate/referral)   => line.total_amount
          doctor discount (% on the line-net subtotal)
          bill goodwill discount (other_discount, flat)       => grand_total
        """
        for rec in self:
            total_wo_disc = 0.0
            total_after_line_discounts = 0.0
            line_discount_total = 0.0
            scheme_total = 0.0

            for line in rec.bill_register_line_id:
                qty = line.product_qty or 0.0
                price = line.price or 0.0

                total_wo_disc += price * qty
                total_after_line_discounts += (line.total_amount or 0.0)
                line_discount_total += (line.total_discount or 0.0)
                scheme_total += (line.scheme_discount_amt or 0.0)

            rec.total_without_discount = total_wo_disc
            rec.total = total_after_line_discounts
            rec.scheme_discount_total = scheme_total

            # doctor discount: % on the line-net subtotal
            rec.doctor_discount_amt = (rec.total or 0.0) * (rec.doctors_discounts or 0.0) / 100.0

            # total discount amount (all line discounts + doctor + goodwill)
            rec.after_discount = line_discount_total + rec.doctor_discount_amt + (rec.other_discount or 0.0)

            # grand total after doctor discount and goodwill discount
            rec.grand_total = (rec.total or 0.0) - rec.doctor_discount_amt - (rec.other_discount or 0.0)

            # due
            rec.due = (rec.grand_total or 0.0) - (rec.paid or 0.0)

    def _find_referral_config(self):
        """Return the active commission/discount agreement for this bill's
        referring doctor or broker, if any (used for the default referral discount).

        The agreement model lives in the optional 'leih_commission' module; if it
        is not installed, referral-based scheme discount is simply skipped."""
        self.ensure_one()
        if 'commission.configuration' not in self.env:
            return False
        # sudo: a billing user need not have commission access to get the
        # referral's default discount.
        Config = self.env['commission.configuration'].sudo()
        config = Config.browse()
        if self.ref_doctors:
            config = Config.search([('doctor_id', '=', self.ref_doctors.id)], limit=1)
        if not config and self.referral:
            config = Config.search([('broker_id', '=', self.referral.id)], limit=1)
        return config

    @api.depends('bill_register_payment_line_id.amount')
    def _compute_paid(self):
        for rec in self:
            rec.paid = sum(rec.bill_register_payment_line_id.mapped('amount'))

    @api.depends('payment_type', 'paid')
    def _compute_service_charge(self):
        for rec in self:
            rec.service_charge = 0.0
            rec.to_be_paid = rec.paid or 0.0

            if rec.payment_type and rec.payment_type.active:
                interest = rec.payment_type.service_charge or 0.0
                if interest > 0 and rec.paid:
                    rec.service_charge = (rec.paid * interest) / 100.0
                    rec.to_be_paid = rec.paid + rec.service_charge

    # -------------------------------------------------------------------------
    # ONCHANGE (optional extra UX)
    # -------------------------------------------------------------------------
    @api.onchange("payment_type", "paid")
    def _onchange_payment_type(self):
        # This is optional because compute already handles it,
        # but onchange makes UI feel instant.
        for rec in self:
            rec._compute_service_charge()
            rec._compute_totals()

    # -------------------------------------------------------------------------
    # CREATE / WRITE
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        # basic validation
        for vals in vals_list:
            if vals.get("due") is not None and vals.get("due") < 0:
                raise UserError(_("Check paid and grand total!"))

            # Optional: keep your diagnostic-bill detection (same logic as your file)
            child_ids = [
                "MRI", 'X-Ray', 'Radiology & Imaging', 'Pathology', 'Bio-Chemistry', 'Haematology', 'Serology',
                'Micro-Biology', 'CT Scan', 'USG', 'Diagnostic', 'X-Ray', 'Echocardiogram', 'Hormone', 'Immunology'
            ]

            depts = []
            for cmd in vals.get('bill_register_line_id', []):
                # Supporting items (consumables) are not part of the diagnostic /
                # non-diagnostic department consistency rule.
                if cmd[0] == 0 and cmd[2] and cmd[2].get('is_support_line'):
                    continue
                if cmd[0] == 0 and cmd[2] and cmd[2].get('department'):
                    d = cmd[2]['department']
                    if d not in depts:
                        depts.append(d)

            vals['diagonostic_bill'] = False
            intersection = list(set(child_ids) & set(depts))
            if intersection and len(intersection) == len(depts):
                vals['diagonostic_bill'] = True
            elif intersection and len(intersection) != len(depts):
                raise UserError(_('This investigation has diagnosis and others department mix up'))

        # sequence for name
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = seq.next_by_code("bill.register") or "New"

        records = super().create(vals_list)
        records._reconcile_support_lines()

        # Initial counter payment -> first money receipt
        for rec in records:
            if rec.down_payment and rec.down_payment > 0:
                rec._register_payment(rec.down_payment)

        return records

    def _reconcile_support_lines(self):
        """Keep supporting lines in sync with the main items on the bill: one line
        per supporting item, quantity summed across the main tests that need it.
        Runs on save so removals/additions of main items also update or drop the
        supporting line. Idempotent and safe to re-run."""
        Line = self.env['bill.register.line'].with_context(skip_support_reconcile=True)
        for bill in self:
            lines = bill.bill_register_line_id
            desired = bill._desired_support_qty(lines.filtered(lambda l: not l.is_support_line))
            seen = set()
            to_unlink = Line.browse()
            for sl in lines.filtered(lambda l: l.is_support_line):
                sid = sl.name.id
                if sid in desired and sid not in seen:
                    if sl.product_qty != desired[sid]:
                        sl.product_qty = desired[sid]
                    seen.add(sid)
                else:
                    to_unlink |= sl
            for sid, qty in desired.items():
                if sid in seen:
                    continue
                sup_entry = self.env['examination.entry'].browse(sid)
                vals = Line._prepare_exam_values(sup_entry)
                vals.update({
                    'name': sid,
                    'bill_register_id': bill.id,
                    'product_qty': qty,
                    'is_support_line': True,
                })
                Line.create(vals)
            if to_unlink:
                to_unlink.unlink()

    # -------------------------------------------------------------------------
    # PAYMENTS
    # -------------------------------------------------------------------------
    def _register_payment(self, amount, payment_type=None, date=None, card_no=None, bank_name=None):
        """Single entry point for collecting money against a bill.

        Creates a money receipt + a payment line; ``paid``/``due`` then recompute
        from the payment lines. Used by both the initial down payment (at create)
        and the Add Payment wizard so the logic stays in one place.
        """
        self.ensure_one()
        amount = amount or 0.0
        if amount <= 0:
            return self.env['leih.money.receipt']
        if amount > (self.due or 0.0) + 0.01:
            raise UserError(_("Payment (%s) exceeds the due amount (%s).") % (amount, self.due or 0.0))

        date = date or fields.Date.context_today(self)
        ptype = payment_type or self.payment_type
        money_receipt = self.env['leih.money.receipt'].create({
            'date': date,
            'bill_id': self.id,
            'amount': amount,
            'bill_total_amount': self.grand_total or 0.0,
            'due_amount': (self.due or 0.0) - amount,
            'p_type': 'due_payment' if (self.paid or 0.0) > 0 else 'advance',
            'already_collected': True,
            'diagonostic_bill': self.diagonostic_bill,
            'payment_type': ptype.id if ptype else False,
            'user_id': self.env.user.id,
        })
        self.env['bill.register.payment.line'].create({
            'bill_register_payment_line_id': self.id,
            'date': date,
            'amount': amount,
            'payment_type': ptype.id if ptype else False,
            'card_no': self.card_no if card_no is None else card_no,
            'bank_name': self.bank_name if bank_name is None else bank_name,
            'money_receipt_id': money_receipt.id,
        })
        return money_receipt

    def write(self, vals):
        if vals.get("due") is not None and vals.get("due") < 0:
            raise UserError(_("Check paid and grand total!"))
        res = super().write(vals)
        # When the item lines change (a main item added/removed/edited), keep the
        # supporting lines and their quantities in sync.
        if 'bill_register_line_id' in vals and not self.env.context.get('skip_support_reconcile'):
            self._reconcile_support_lines()
        return res

    # -------------------------------------------------------------------------
    # Your existing actions (kept minimal; you can paste your old ones below)
    # -------------------------------------------------------------------------
    def bill_confirm(self):
        # Keep your original code here if needed.
        # I am not rewriting it fully since your request was totals + numbering.
        # raise UserError(_("bill_confirm(): paste your existing confirm logic here (unchanged)."))
        self.ensure_one()
        self.state = 'confirmed'
        self._generate_lab_items()
        return True

    def action_generate_lab_items(self):
        """Manual trigger from form button. Idempotent."""
        for bill in self:
            bill._generate_lab_items()
        return True

    def _generate_lab_items(self):
        """Create lab.specimen records (grouped by tube_color + department) and
        examination.result records for every lab test on this bill.

        Idempotent: tests whose result already exists for this bill are skipped.
        Radiology / descriptive / tube-less tests bypass the specimen layer.
        """
        self.ensure_one()
        if not self.bill_register_line_id:
            return
        Specimen = self.env['lab.specimen']
        Result = self.env['examination.result']

        existing_entry_ids = set(self.lab_result_ids.mapped('entry_id').ids)
        # Consumables (test tube, bed sheet, ...) are billed but never reported on:
        # anything configured as somebody's supporting item is excluded, whether it
        # was pulled in automatically or typed on the bill by hand.
        support_entry_ids = set(self.env['examination.support.item'].search(
            []).mapped('support_entry_id').ids)

        # Group test lines that share a tube
        groups = {}            # key -> list of (entry, doctor)
        direct_lines = []      # (entry, doctor) — no specimen needed

        for line in self.bill_register_line_id:
            entry = line.name
            if not entry or entry.id in existing_entry_ids:
                continue
            # Only diagnostic/lab items produce lab results & specimens.
            if (entry.service_group or 'diagnostic') != 'diagnostic':
                continue
            if line.is_support_line or entry.lab_not_required or entry.id in support_entry_ids:
                continue
            if entry.category in ('radiology', 'descriptive') or not entry.tube_color_id:
                direct_lines.append((entry, line.assign_doctors))
                continue
            if entry.needs_separate_tube:
                key = ('solo', entry.id)
            else:
                key = (entry.tube_color_id.id, entry.department.id if entry.department else 0)
            groups.setdefault(key, []).append((entry, line.assign_doctors))

        # Make a specimen per group and a result per test on the specimen
        for entries in groups.values():
            first_entry = entries[0][0]
            specimen = Specimen.create({
                'patient_id': self.patient_name.id,
                'bill_register_id': self.id,
                'tube_color_id': first_entry.tube_color_id.id,
                'department_id': first_entry.department.id if first_entry.department else False,
            })
            for entry, doctor in entries:
                Result.create({
                    'patient_id': self.patient_name.id,
                    'entry_id': entry.id,
                    'doctor_id': (doctor or self.ref_doctors).id if (doctor or self.ref_doctors) else False,
                    'specimen_id': specimen.id,
                    'bill_register_id': self.id,
                })

        # Tests with no sample collection (radiology / descriptive)
        for entry, doctor in direct_lines:
            Result.create({
                'patient_id': self.patient_name.id,
                'entry_id': entry.id,
                'doctor_id': (doctor or self.ref_doctors).id if (doctor or self.ref_doctors) else False,
                'bill_register_id': self.id,
            })

    def action_view_lab_specimens(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lab Specimens',
            'res_model': 'lab.specimen',
            'view_mode': 'list,form',
            'domain': [('bill_register_id', '=', self.id)],
            'context': {'default_bill_register_id': self.id, 'default_patient_id': self.patient_name.id},
        }

    def amount_in_words(self, amount=None):
        """Spell out an amount in the company currency, e.g. 'Three Thousand Taka'.

        Defaults to the paid amount, which is what the counter slip prints."""
        self.ensure_one()
        currency = self.env.company.currency_id
        if not currency:
            return ''
        return currency.amount_to_text(self.paid if amount is None else amount)

    def action_print_bill_slip(self):
        """Counter slip / patient copy of this bill."""
        self.ensure_one()
        return self.env.ref('leih19.action_report_bill_register_slip').report_action(self)

    def action_print_tube_stickers(self):
        """Print tube stickers for all specimens of this bill."""
        self.ensure_one()
        if not self.specimen_ids:
            raise UserError(_("No tubes/specimens for this bill yet. Confirm the bill first."))
        return self.env.ref('leih19.action_report_lab_specimen_sticker').report_action(self.specimen_ids)

    def action_view_lab_results(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lab Results',
            'res_model': 'examination.result',
            'view_mode': 'list,form',
            'domain': [('bill_register_id', '=', self.id)],
            'context': {'default_bill_register_id': self.id, 'default_patient_id': self.patient_name.id},
        }

    def action_print_lab_reports(self):
        """Print all the bill's lab tests merged; warn if any aren't verified."""
        self.ensure_one()
        return self._print_lab_reports_checked()

    def _print_lab_reports_checked(self):
        """Print verified/released results; if some tests are still pending,
        open a confirmation wizard listing them (Print Verified Only / Cancel)."""
        self.ensure_one()
        results = self.lab_result_ids
        verified = results.filtered(lambda r: r.state in ('verified', 'released'))
        pending = results.filtered(lambda r: r.state in ('draft', 'in_progress'))
        if not verified:
            raise UserError(_(
                "No verified or released lab results yet. "
                "Enter the values and verify each test before printing."
            ))
        if pending:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Some tests are not verified'),
                'res_model': 'lab.print.confirm',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_bill_register_id': self.id,
                    'default_message': _(
                        "These tests are NOT verified yet and will be left out of the print:\n\n%s\n\n"
                        "Print the verified tests only?"
                    ) % ", ".join(pending.mapped('entry_id.name')),
                },
            }
        return self.env.ref('leih19.action_report_examination_result').report_action(verified)

    def bill_cancel(self):
        self.ensure_one()
        self.state = 'cancelled'
        return True

    
    
    def btn_pay_bill(self):
        self.ensure_one()

        if self.state == 'pending':
            raise UserError(_('Please Confirm and Print the Bill'))

        if (self.due or 0.0) <= 0:
            raise UserError(_('Nothing to Pay. Already fully paid.'))

        return {
            'name': _("Pay Invoice"),
            'type': 'ir.actions.act_window',
            'res_model': 'bill.register.payment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_bill_id': self.id,
                'default_date': fields.Date.context_today(self),
                'default_amount': self.due,
                'default_payment_type': self.payment_type.id if self.payment_type else False,
            }
        }

    def add_discount(self):
        self.ensure_one()
        return {
            'name': _("Discount"),
            'type': 'ir.actions.act_window',
            'res_model': 'discount',
            'view_mode': 'form',
            'target': 'new',
            'context': {'pi_id': self.id}
        }

    def add_new_test(self):
        self.ensure_one()
        return {
            'name': _("Pay Invoice"),
            'type': 'ir.actions.act_window',
            'res_model': 'add.bill',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'bill_id': self.id,
                'default_price': 500,
                'default_total_amount': 200,
            }
        }


# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import date, timedelta


from odoo import api, fields, models
from datetime import date, timedelta


class BillRegisterLine(models.Model):
    _name = 'bill.register.line'
    _description = 'BillRegisterLine'

    name = fields.Many2one(
        'examination.entry',
        string='Item Name',
        ondelete='restrict'
    )
    bill_register_id = fields.Many2one(
        'bill.register',
        string='Information',
        ondelete='cascade'
    )
    department = fields.Char('Department')
    product_qty = fields.Float('Quantity', default=1.0)
    delivery_date = fields.Date('Delivery Date')
    date = fields.Datetime('Date', readonly=True, default=fields.Datetime.now)

    price = fields.Float('Price')
    discount = fields.Float('Discount (%)', default=0.0)
    flat_discount = fields.Float('Flat Discount', default=0.0)
    scheme_discount = fields.Float(
        'Scheme Discount (%)', compute='_compute_scheme_discount', store=True, readonly=False,
        help='Auto-filled from the corporate client / referral agreement. You can override it.')

    gross_amount = fields.Float('Gross', compute='_compute_amounts', store=True,
                                help='List price × quantity, before any discount.')
    total_discount = fields.Float('Total Discount', compute='_compute_amounts', store=True)
    discount_percent = fields.Float('Manual Disc. Amount', compute='_compute_amounts', store=True)
    scheme_discount_amt = fields.Float('Scheme Disc. Amount', compute='_compute_amounts', store=True)
    total_amount = fields.Float('Total Amount', compute='_compute_amounts', store=True)
    paid_allocated = fields.Float('Paid (allocated)', compute='_compute_paid_allocated', store=True,
                                  help='Bill payment split across items in proportion to each item net amount.')

    # --- Analytics helpers (cross-bill reporting) ---
    department_id = fields.Many2one(
        'diagnosis.department', string='Department (ref)',
        compute='_compute_department_id', store=True,
        help='Department of the test, for grouping in reports.')
    service_group = fields.Selection(
        related='name.service_group', store=True, string='Service Group',
        help='Diagnostic / physiotherapy / dental / ... of the item, for income reports.')
    bill_state = fields.Selection(related='bill_register_id.state', store=True, string='Bill Status')
    bill_date = fields.Datetime(related='bill_register_id.date', store=True, string='Bill Date')

    assign_doctors = fields.Many2one('doctors.profile', string='Doctor')
    commission_paid = fields.Boolean('Commission Paid')

    # --- Supporting-item traceability ---
    is_support_line = fields.Boolean(
        'Supporting Item', default=False,
        help='Auto-generated line for a supporting item of another billed item.')
    source_entry_id = fields.Many2one(
        'examination.entry', string='Added For',
        help='The main item that pulled this supporting item into the bill.')

    @api.depends('name')
    def _compute_department_id(self):
        for rec in self:
            rec.department_id = rec.name.department if rec.name else False

    @api.depends('total_amount', 'bill_register_id.paid', 'bill_register_id.total')
    def _compute_paid_allocated(self):
        for rec in self:
            bill = rec.bill_register_id
            base = bill.total if bill else 0.0
            if bill and base:
                rec.paid_allocated = (bill.paid or 0.0) * (rec.total_amount or 0.0) / base
            else:
                rec.paid_allocated = 0.0

    def _prepare_exam_values(self, exam):
        if not exam:
            return {}

        required_days = exam.required_time or 0
        return {
            'department': exam.department.name if exam.department else False,
            'product_qty': 1.0,
            'price': exam.rate or 0.0,
            'delivery_date': date.today() + timedelta(days=required_days),
        }

    @api.onchange('name')
    def _onchange_name(self):
        for rec in self:
            _logger.warning("ONCHANGE FIRED: %s", rec.name.id if rec.name else False)
            if not rec.name:
                rec.department = False
                rec.product_qty = 1.0
                rec.price = 0.0
                rec.delivery_date = False
                return

            vals = rec._prepare_exam_values(rec.name)
            rec.update(vals)

    @api.depends('product_qty', 'price', 'discount', 'flat_discount', 'scheme_discount')
    def _compute_amounts(self):
        for rec in self:
            qty = rec.product_qty or 0.0
            price = rec.price or 0.0
            base = qty * price

            # 1) manual line discount: percentage then flat
            manual_pct_amt = base * (rec.discount or 0.0) / 100.0
            running = base - manual_pct_amt - (rec.flat_discount or 0.0)
            if running < 0.0:
                running = 0.0

            # 2) scheme discount (corporate / referral %) on the remaining amount
            scheme_amt = running * (rec.scheme_discount or 0.0) / 100.0
            running = running - scheme_amt

            rec.gross_amount = base
            rec.discount_percent = manual_pct_amt
            rec.scheme_discount_amt = scheme_amt
            rec.total_amount = running
            rec.total_discount = base - running

    # --- Auto scheme discount from corporate client / referral agreement ---
    @staticmethod
    def _date_in_range(today, start, end):
        return (not start or today >= start) and (not end or today <= end)

    @api.depends('name', 'bill_register_id.corporate_client_id',
                 'bill_register_id.ref_doctors', 'bill_register_id.referral')
    def _compute_scheme_discount(self):
        for rec in self:
            rec.scheme_discount = rec._get_scheme_discount_percent()

    def _get_scheme_discount_percent(self):
        """Resolve the auto discount % for this line:
        1) corporate client contract (test-specific > department > overall), then
        2) referring doctor / broker default discount (capped by its max)."""
        self.ensure_one()
        bill = self.bill_register_id
        entry = self.name
        if not bill or not entry:
            return 0.0
        today = fields.Date.context_today(self)
        dept = entry.department

        # 1) Corporate client contract
        cc = bill.corporate_client_id
        if cc and self._date_in_range(today, cc.from_date, cc.to_date):
            # percentage (variance) lines: test-specific first, then department
            lines = cc.discount_donfiguration_line_ids.filtered(
                lambda l: l.applicable and l.variance_amount)
            match = lines.filtered(lambda l: l.test_id and l.test_id == entry)[:1]
            if not match and dept:
                match = lines.filtered(lambda l: l.department_id and l.department_id == dept)[:1]
            if match:
                return match.variance_amount
            return cc.overall_discount or 0.0

        # 2) Referral (doctor / broker) default discount
        config = bill._find_referral_config()
        if config and self._date_in_range(today, config.start_date, config.end_date):
            pct = config.overall_default_discount or 0.0
            if config.max_default_discount:
                pct = min(pct, config.max_default_discount)
            return pct

        return 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            exam_id = vals.get('name')
            if exam_id:
                exam = self.env['examination.entry'].browse(exam_id)
                auto_vals = self._prepare_exam_values(exam)
                for key, value in auto_vals.items():
                    vals.setdefault(key, value)
        records = super().create(vals_list)
        # Reconcile at the bill level so supporting items are consolidated into a
        # single line with a summed quantity. Skipped when we are ourselves
        # creating supporting lines (avoids recursion).
        if not self.env.context.get('skip_support_reconcile'):
            bills = records.filtered(lambda l: not l.is_support_line).bill_register_id
            if bills:
                bills._reconcile_support_lines()
        return records

    def write(self, vals):
        if vals.get('name'):
            exam = self.env['examination.entry'].browse(vals['name'])
            auto_vals = self._prepare_exam_values(exam)
            for key, value in auto_vals.items():
                vals.setdefault(key, value)
        return super().write(vals)

class BillRegisterPaymentLine(models.Model):
    _name = 'bill.register.payment.line'
    _description = 'Bill Register Payment Line'

    bill_register_payment_line_id = fields.Many2one('bill.register', string='Bill register payment', ondelete='cascade')
    date = fields.Date("Date")
    amount = fields.Float('Amount')
    payment_type = fields.Many2one('payment.type', string='Payment Type')
    card_no = fields.Char('Card Number')
    bank_name = fields.Char('Bank Name')
    money_receipt_id = fields.Many2one('leih.money.receipt', string='Money Receipt ID')


class BillJournalRelation(models.Model):
    _name = 'bill.journal.relation'
    _description = 'Bill Journal Relation'

    bill_journal_relation_id = fields.Many2one('bill.register', string='Bill register', ondelete='cascade')
    admission_journal_relation_id = fields.Many2one('leih.admission', string='Admission Journal')
    general_admission_journal_relation_id = fields.Many2one('hospital.admission', string='General Admission Journal')

    journal_move_id = fields.Many2one('account.move', string="Journal Entry", ondelete='set null')

    # legacy integer if you still show it in tree view
    journal_id = fields.Integer("Journal Id")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            jmid = vals.get('journal_move_id')
            if jmid and not vals.get('journal_id'):
                # in create payload many2one is usually an int id
                vals['journal_id'] = jmid if isinstance(jmid, int) else False
        return super().create(vals_list)