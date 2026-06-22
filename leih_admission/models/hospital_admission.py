from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HospitalAdmission(models.Model):
    """Phase A: payments single source of truth.

    ``paid`` becomes the sum of confirmed money receipts linked to the
    admission, so ``due`` (computed in the base ``_compute_totals``) is always
    correct. All payments flow through ``_register_admission_payment`` -- the
    admission is the single money entry point.
    """
    _inherit = 'hospital.admission'

    # Override: paid is now derived, never typed by hand.
    paid = fields.Float(
        string="Paid", compute='_compute_paid_amount', store=True, readonly=True,
        help="Total confirmed admission payments (sum of money receipts).")
    down_payment = fields.Float(
        "Advance (Paid Now)",
        help="Advance collected when the admission is first saved. "
             "Generates the first money receipt automatically; later payments use the Payment button.")

    charge_ids = fields.One2many(
        'hospital.admission.charge', 'admission_id', string='Charges')

    @api.depends('money_receipt_ids.amount', 'money_receipt_ids.state')
    def _compute_paid_amount(self):
        for rec in self:
            rec.paid = sum(
                rec.money_receipt_ids
                .filtered(lambda m: m.state == 'confirm')
                .mapped('amount')
            )

    def _register_admission_payment(self, amount, payment_type=None, date=None, account_number=None):
        """Single entry point for collecting money against an admission.

        Creates a money receipt (+ a payment line for display); ``paid``/``due``
        then recompute from the receipts. Used by the initial advance (at create)
        and the Payment wizard so the logic lives in one place."""
        self.ensure_one()
        amount = amount or 0.0
        if amount <= 0:
            return self.env['leih.money.receipt']
        # No over-due guard: IPD advance deposits are taken before charges
        # exist, so paid may exceed grand_total (the excess is a credit / due
        # goes negative).
        date = date or fields.Date.context_today(self)
        ptype = payment_type or self.payment_type
        money_receipt = self.env['leih.money.receipt'].create({
            'date': date,
            'general_admission_id': self.id,
            'amount': amount,
            'bill_total_amount': self.grand_total or 0.0,
            'due_amount': (self.due or 0.0) - amount,
            'p_type': 'due_payment' if (self.paid or 0.0) > 0 else 'advance',
            'already_collected': True,
            'type': ptype.id if ptype else False,
            'user_id': self.env.user.id,
        })
        self.env['general.admission.payment.line'].create({
            'admission_payment_line_id': self.id,
            'date': date,
            'amount': amount,
            'type': ptype.name if ptype else '',
            'card_no': account_number or '',
            'money_receipt_id': money_receipt.id,
        })
        return money_receipt

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Initial advance -> first money receipt
        for rec in records:
            if rec.down_payment and rec.down_payment > 0:
                rec._register_admission_payment(rec.down_payment)
        return records

    # -------------------------------------------------------------------------
    # CHARGE LEDGER + TOTALS  (Phase B)
    # -------------------------------------------------------------------------
    # examination.entry.service_group -> charge.service_type
    _SERVICE_GROUP_MAP = {
        'diagnostic': 'diagnostic',
        'physiotherapy': 'physiotherapy',
        'dental': 'dental',
        'consultation': 'consultation',
        'procedure': 'procedure',
        'oxygen': 'oxygen',
        'consumable': 'other',
        'other': 'other',
    }
    # hospital.bed.bed_type -> charge.service_type
    _BED_TYPE_MAP = {
        'general': 'bed', 'cabin': 'cabin', 'icu': 'icu',
        'nicu': 'nicu', 'hdu': 'hdu', 'other': 'bed',
    }
    # charge sources this model owns; other modules (e.g. pharmacy) manage their own.
    _FEEDER_MODELS = (
        'hospital.admission.line', 'hospital.bill.line', 'hospital.bed.line',
        'doctor.profile.admission.line', 'hospital.medicine.line',
    )

    @api.onchange('other_discount')
    def _onchange_other_discount(self):
        # Superseded by _compute_totals (charge ledger). Override the legacy
        # onchange so it no longer overwrites grand_total / due on the form.
        return

    @api.onchange('doctors_discounts')
    def _onchange_doc_discount(self):
        return

    @api.depends(
        'charge_ids.total_amount',
        'leih_admission_line_id.total_amount',
        'hospital_bed_line_id.total_amount',
        'hospital_bill_line_id.total_amount',
        'hospital_doctor_line_id.total_amount',
        'doctors_discounts', 'other_discount', 'paid', 'investigation_paid',
    )
    def _compute_totals(self):
        """Totals come from the unified charge ledger once it is populated
        (press Calculate Payable). Before that, fall back to the legacy typed
        line models so existing admissions keep correct figures."""
        for rec in self:
            if rec.charge_ids:
                subtotal = sum(rec.charge_ids.mapped('total_amount'))
                gross = sum((c.qty or 0.0) * (c.unit_price or 0.0) for c in rec.charge_ids)
            else:
                subtotal = (
                    sum(rec.leih_admission_line_id.mapped('total_amount'))
                    + sum(rec.hospital_bed_line_id.mapped('total_amount'))
                    + sum(rec.hospital_bill_line_id.mapped('total_amount'))
                    + sum(rec.hospital_doctor_line_id.mapped('total_amount'))
                )
                gross = subtotal

            doctor_disc = subtotal * (rec.doctors_discounts or 0.0) / 100.0
            rec.total_without_discount = gross
            rec.total = subtotal
            rec.after_discount = doctor_disc + (rec.other_discount or 0.0)
            rec.grand_total = subtotal - doctor_disc - (rec.other_discount or 0.0)
            rec.due = rec.grand_total - (rec.paid + rec.investigation_paid)

    @staticmethod
    def _to_float(value):
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    def _bed_days(self, line):
        """Whole days for a bed occupancy: admit/start -> end or now, min 1."""
        start = line.start_date or self.date
        end = line.end_date or fields.Datetime.now()
        if not start:
            return 1.0
        delta = end - start
        days = delta.days + (1 if delta.seconds or delta.days == 0 else 0)
        return float(max(1, days))

    def _statement_summary(self):
        """Charges summarized to ONE line per service type (e.g. all physio
        items roll up to a single 'Physiotherapy' total) for the printed
        statement. Returns a sorted list of {label, amount}."""
        self.ensure_one()
        labels = dict(self.env['hospital.admission.charge']._fields['service_type'].selection)
        groups = {}
        for c in self.charge_ids:
            groups[c.service_type] = groups.get(c.service_type, 0.0) + (c.total_amount or 0.0)
        rows = [{'label': labels.get(k, k), 'amount': v} for k, v in groups.items()]
        rows.sort(key=lambda r: r['label'])
        return rows

    def action_print_statement(self):
        self.ensure_one()
        return self.env.ref('leih_admission.action_report_admission_statement').report_action(self)

    def action_new_investigation_bill(self):
        """Open a new Bill Register pre-linked to this admission and patient, so
        diagnostics go through the lab pipeline (specimen / sample collection /
        result) and then pull back in via Calculate Payable."""
        self.ensure_one()
        if not self.patient_name:
            raise UserError(_("Select a patient on the admission first."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Investigation Bill'),
            'res_model': 'bill.register',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_patient_name': self.patient_name.id,
                'default_general_admission_id': self.id,
                'default_ref_doctors': self.ref_doctors.id if self.ref_doctors else False,
            },
        }

    def action_calculate_payable(self):
        """Rebuild the charge ledger from every service source, then totals/due
        recompute. Recurring (bed) charges are recomputed to today on each run."""
        for rec in self:
            rec.calculate_bill()  # refresh diagnostics into hospital.bill.line
            rec._rebuild_charges()
        return True

    def _rebuild_charges(self):
        self.ensure_one()
        Charge = self.env['hospital.admission.charge']
        # wipe only the charges this model owns; keep manual ones (no source)
        # and charges managed by other modules (e.g. pharmacy).
        self.charge_ids.filtered(lambda c: c.source_model in self._FEEDER_MODELS).unlink()
        vals_list = []

        # 1) Investigations entered directly on the admission
        for il in self.leih_admission_line_id:
            entry = il.name
            sg = (entry.service_group if entry else 'diagnostic') or 'diagnostic'
            vals_list.append({
                'admission_id': self.id,
                'service_type': self._SERVICE_GROUP_MAP.get(sg, 'other'),
                'item_id': entry.id if entry else False,
                'description': entry.name if entry else (il.department or 'Item'),
                'unit_id': entry.department.id if entry and entry.department else False,
                'qty': il.product_qty or 1.0,
                'unit_price': il.price,
                'discount': il.total_discount or 0.0,
                'source_model': 'hospital.admission.line', 'source_res_id': il.id,
            })

        # 2) Diagnostics / service bills pulled into hospital.bill.line
        for bl in self.hospital_bill_line_id:
            entry = bl.item_name
            sg = (entry.service_group if entry else 'diagnostic') or 'diagnostic'
            vals_list.append({
                'admission_id': self.id,
                'service_type': self._SERVICE_GROUP_MAP.get(sg, 'diagnostic'),
                'item_id': entry.id if entry else False,
                'description': entry.name if entry else (bl.name or bl.department or 'Item'),
                'unit_id': entry.department.id if entry and entry.department else False,
                'qty': bl.product_qty or 1.0,
                'unit_price': bl.price,
                'discount': bl.total_discount or 0.0,
                'date': bl.bill_created_date or bl.date,
                'source_model': 'hospital.bill.line', 'source_res_id': bl.id,
            })

        # 3) Bed / Cabin / ICU / NICU (days x per-day rate, recomputed)
        for bd in self.hospital_bed_line_id:
            bed = bd.bed_no
            stype = self._BED_TYPE_MAP.get(bed.bed_type if bed else 'general', 'bed')
            days = self._bed_days(bd)
            vals_list.append({
                'admission_id': self.id,
                'service_type': stype,
                'description': (bed.name if bed else 'Bed') + (' (%d day/s)' % int(days)),
                'qty': (bd.bed_qty or 1.0) * days,
                'unit_price': bd.perday_charge or (bed.perday_charge if bed else 0.0),
                'discount': 0.0,
                'date': bd.start_date or self.date,
                'source_model': 'hospital.bed.line', 'source_res_id': bd.id,
            })

        # 4) Doctor fees
        for dl in self.hospital_doctor_line_id:
            vals_list.append({
                'admission_id': self.id,
                'service_type': 'doctor',
                'description': dl.name or (dl.doctor_profile_id.name if dl.doctor_profile_id else 'Doctor Fee'),
                'provider_id': dl.doctor_profile_id.id if dl.doctor_profile_id else False,
                'qty': dl.doctor_visit_qty or 1.0,
                'unit_price': dl.visit_fee,
                'discount': 0.0,
                'source_model': 'doctor.profile.admission.line', 'source_res_id': dl.id,
            })

        # 5) Medicine (charge-to-room; fields are stored as text in legacy model)
        for ml in self.hospital_medicine_line_id:
            vals_list.append({
                'admission_id': self.id,
                'service_type': 'medicine',
                'description': ml.product_name.product_name if ml.product_name else 'Medicine',
                'qty': self._to_float(ml.product_qty) or 1.0,
                'unit_price': self._to_float(ml.unit_price),
                'discount': 0.0,
                'source_model': 'hospital.medicine.line', 'source_res_id': ml.id,
            })

        if vals_list:
            Charge.create(vals_list)
        return True
