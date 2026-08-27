from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from num2words import num2words
from datetime import date, timedelta


class HospitalAdmission(models.Model):
    _name = "hospital.admission"
    _description = "Hospital Admission"
    _order = "id desc"

    name = fields.Char(string="Name", copy=False, readonly=True, default="New")
    mobile = fields.Char(string="Mobile")
    patient_id = fields.Char(
        string="Patient Id",
        related="patient_name.patient_id",
        store=True,
        readonly=True,
    )
    patient_name = fields.Many2one("patient.info", string="Patient Name", required=True)
    address = fields.Char(string="Address")
    age = fields.Char(string="Age")
    sex = fields.Char(string="Sex")
    ref_doctors = fields.Many2one("doctors.profile", string="Referred by (Doctor)")
    operation_date = fields.Date(string="Operation Date")
    release_note_date = fields.Datetime(string="Release Date")
    release_note = fields.Text(string="Release Note")
    package_name = fields.Many2one("examine.package", string="Package")

    leih_admission_line_id = fields.One2many(
        "hospital.admission.line", "leih_admission_id", string="Investigations"
    )
    guarantor_line_id = fields.One2many(
        "hospital.patient.guarantor", "admission_id", string="Guarantor Name"
    )
    bill_register_admission_line_id = fields.One2many(
        "bill.register.general.admission.line",
        "general_admission_line_id",
        string="Bill Register",
    )
    admission_payment_line_id = fields.One2many(
        "general.admission.payment.line",
        "admission_payment_line_id",
        string="Admission Payment",
    )
    admission_journal_relation_id = fields.One2many(
        "bill.journal.relation",
        "general_admission_journal_relation_id",
        string="Journal",
    )
    hospital_doctor_line_id = fields.One2many(
        "doctor.profile.admission.line",
        "hospital_doctor_line_item",
        string="Doctor",
    )
    hospital_medicine_line_id = fields.One2many(
        "hospital.medicine.line",
        "hospital_medicine_line_item",
        string="Medicine",
    )
    hospital_bed_line_id = fields.One2many(
        "hospital.bed.line",
        "hospital_bed_item_id",
        string="Bed",
    )
    hospital_bill_line_id = fields.One2many(
        "hospital.bill.line",
        "hospital_admission_id",
        string="Bill",
    )

    money_receipt_ids = fields.One2many(
    'leih.money.receipt',
    'general_admission_id',
    string='Money Receipts'
    
    )

    emergency = fields.Boolean(string="Emergency Department")
    total_without_discount = fields.Float(string="Total without discount", compute="_compute_totals", store=True)
    total = fields.Float(string="Total", compute="_compute_totals", store=True)
    doctors_discounts = fields.Float(string="Discount(%)")
    after_discount = fields.Float(string="Discount Amount", compute="_compute_totals", store=True)
    other_discount = fields.Float(string="Other Discount")
    discount_remarks = fields.Char(string="Discount Remarks")
    grand_total = fields.Float(string="Grand Total", compute="_compute_totals", store=True)
    investigation_total = fields.Float(string="Investigation Total", default=0.0)
    investigation_paid = fields.Float(string="Investigation Paid", default=0.0)
    advance = fields.Float(string="Advance", default=0.0)
    paid = fields.Float(string="Paid", default=0.0)
    due = fields.Float(string="Due", compute="_compute_totals", store=True)

    type = fields.Selection(
        [("cash", "Cash"), ("bank", "Bank")],
        string="Payment Type",
    )
    card_no = fields.Char(string="Card No.")
    bank_name = fields.Char(string="Bank Name")
    date = fields.Datetime(string="Date", default=fields.Datetime.now, readonly=True)
    user_id = fields.Many2one("res.users", string="Assigned to", default=lambda self: self.env.user)
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("activated", "Admitted"),
            ("released", "Released"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="pending",
        readonly=True,
        tracking=True,
    )
    emergency_covert_time = fields.Datetime(string="Admission Convert time")
    old_journal = fields.Boolean(string="Old Journal")

    payment_type = fields.Many2one(
        "payment.type",
        string="Payment Type",
        default=lambda self: self._default_payment_type(),
    )
    service_charge = fields.Float(string="Service Charge")
    to_be_paid = fields.Float(string="To be Paid")
    account_number = fields.Char(string="Account Number")

    # --- Guardian / attendant (shown on its own notebook page) ---
    guardian_name = fields.Char(string="Guardian Name")
    guardian_relation = fields.Char(string="Relation with Patient")
    guardian_occupation = fields.Char(string="Guardian Occupation")
    guardian_contact = fields.Char(string="Guardian Contact No")

    # Investigation bills raised for this admitted patient.
    investigation_bill_ids = fields.One2many(
        'bill.register', 'general_admission_id', string='Investigation Bills')

    father_name = fields.Char(string="Father's Name")
    mother_name = fields.Char(string="Mother's Name")
    spouse_name = fields.Char(string="Spouse Name")
    religion = fields.Selection(
        [
            ("islam", "Islam"),
            ("hindu", "Hinduism"),
            ("buddhism", "Buddhism"),
            ("christianity", "Christianity"),
        ],
        string="Religion",
    )
    blood_group = fields.Char(string="Blood Group")
    reffered_to_hospital = fields.Many2one("brokers.info", string="Referred to this hospital by")
    occupation = fields.Char(string="Occupation")
    business_address = fields.Char(string="Business Address")
    admitting_doctor = fields.Many2one("doctors.profile", string="Admitting Doctor")
    bed = fields.Char(string="Bed")

    prescription_count = fields.Integer(string='Prescription Count', compute='_compute_prescription_count')

    def _compute_prescription_count(self):
        Prescription = self.env['doctor.prescription']
        for rec in self:
            rec.prescription_count = Prescription.search_count([('admission_id', '=', rec.id)])

    def action_create_prescription(self):
        self.ensure_one()
        doctor = self.admitting_doctor or self.ref_doctors
        if not self.patient_name:
            raise UserError(_('Please select a patient first.'))
        if not doctor:
            raise UserError(_('Please select an admitting or referred doctor first.'))
        prescription = self.env['doctor.prescription'].create({
            'patient_id': self.patient_name.id,
            'doctor_id': doctor.id,
            'department': doctor.department,
            'source_model': 'hospital.admission',
            'admission_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Prescription'),
            'res_model': 'doctor.prescription',
            'view_mode': 'form',
            'res_id': prescription.id,
            'target': 'current',
        }

    def action_view_prescriptions(self):
        self.ensure_one()
        doctor = self.admitting_doctor or self.ref_doctors
        return {
            'type': 'ir.actions.act_window',
            'name': _('Prescriptions'),
            'res_model': 'doctor.prescription',
            'view_mode': 'list,form',
            'domain': [('admission_id', '=', self.id)],
            'context': {
                'default_patient_id': self.patient_name.id,
                'default_doctor_id': doctor.id if doctor else False,
                'default_admission_id': self.id,
                'default_source_model': 'hospital.admission',
            },
        }

    received_by = fields.Char(string="Received/Registered By")
    clinic_diagnosis = fields.Char(string="Clinical Diagnosis")

    @api.model
    def _default_payment_type(self):
        return self.env["payment.type"].search([("name", "=", "Cash")], limit=1)

    @api.depends(
        "leih_admission_line_id.total_amount",
        "leih_admission_line_id.price",
        "leih_admission_line_id.product_qty",
        "hospital_bed_line_id.total_amount",
        "hospital_bill_line_id.total_amount",
        "hospital_bill_line_id.price",
        "hospital_doctor_line_id.total_amount",
        "doctors_discounts",
        "other_discount",
        "paid",
        "investigation_paid",
    )
    def _compute_totals(self):
        for rec in self:
            investigation_lines_total = sum(rec.leih_admission_line_id.mapped("total_amount"))
            bed_total = sum(rec.hospital_bed_line_id.mapped("total_amount"))
            hospital_bill_total = sum(rec.hospital_bill_line_id.mapped("total_amount"))
            doctor_total = sum(rec.hospital_doctor_line_id.mapped("total_amount"))

            total_without_discount = (
                sum(line.price * line.product_qty for line in rec.leih_admission_line_id)
                + sum(rec.hospital_bed_line_id.mapped("total_amount"))
                + sum(rec.hospital_bill_line_id.mapped("price"))
                + sum(rec.hospital_doctor_line_id.mapped("total_amount"))
            )

            subtotal = investigation_lines_total + bed_total + hospital_bill_total + doctor_total
            discount_amount = 0.0  # old code kept this as zero in onchange_admission_line
            grand_total = subtotal - rec.other_discount

            rec.total_without_discount = total_without_discount
            rec.total = subtotal
            rec.after_discount = discount_amount
            rec.grand_total = grand_total
            rec.due = grand_total - (rec.paid + rec.investigation_paid)

    @api.onchange("patient_name")
    def _onchange_patient_name(self):
        """Fill patient details when a patient is selected or created inline."""
        for rec in self:
            patient = rec.patient_name
            rec.mobile = patient.mobile or False
            rec.address = patient.address or False
            rec.age = patient.age or False
            rec.sex = patient.sex or False

    @api.onchange("package_name")
    def _onchange_package_name(self):
        for rec in self:
            if not rec.package_name:
                continue

            line_commands = [(5, 0, 0)]
            rec.other_discount = rec.package_name.total_without_discount - rec.package_name.total

            ChargeItem = self.env["admission.charge.item"]
            for item in rec.package_name.examine_package_line_id:
                # Package lines are examination entries; admission lines bill
                # from the charge catalogue, so mirror the entry into it.
                charge_item = ChargeItem._from_examination_entry(item.name)
                line_commands.append(
                    (0, 0, {
                        "name": charge_item.id,
                        "total_amount": item.total_amount,
                        "price": item.price,
                        "flat_discount": item.discount,
                        "product_qty": 1,
                    })
                )

            rec.leih_admission_line_id = line_commands

    @api.onchange("payment_type", "paid")
    def _onchange_payment_type(self):
        for rec in self:
            rec.service_charge = 0.0
            rec.to_be_paid = rec.paid
            if rec.payment_type and getattr(rec.payment_type, "active", False):
                interest = rec.payment_type.service_charge or 0.0
                if interest > 0:
                    rec.service_charge = (rec.paid * interest) / 100.0
                    rec.to_be_paid = rec.paid + rec.service_charge

    @api.onchange("paid", "investigation_paid")
    def _onchange_paid(self):
        for rec in self:
            rec.due = rec.grand_total - (rec.paid + rec.investigation_paid)
            if rec.payment_type and rec.payment_type.name == "Visa Card":
                interest = rec.payment_type.service_charge or 0.0
                rec.service_charge = (rec.paid * interest) / 100.0
                rec.to_be_paid = rec.paid + rec.service_charge

    @api.onchange("doctors_discounts")
    def _onchange_doc_discount(self):
        for rec in self:
            discount = rec.doctors_discounts or 0.0
            for line in rec.leih_admission_line_id:
                line.discount_percent = round((line.price * line.product_qty * discount) / 100.0)
                line.discount = discount
                line.total_discount = line.flat_discount + line.discount_percent
                line.total_amount = (line.price - line.total_discount) * line.product_qty

    @api.onchange("other_discount")
    def _onchange_other_discount(self):
        for rec in self:
            gd = rec.total_without_discount - rec.other_discount
            rec.total = gd
            rec.grand_total = gd
            rec.due = rec.grand_total - rec.paid

    def amount_to_text_custom(self, amount, currency="BDT"):
        integer_part = int(amount)
        decimal_part = round((amount - integer_part) * 100)
        text = f"{num2words(integer_part, lang='en').title()} Taka"
        if decimal_part:
            text += f" and {num2words(decimal_part, lang='en').title()} Paisa"
        return text

    def advance_paid(self, name):
        mr = self.env["leih.money.receipt"].search([("general_admission_id", "=", name)])
        advance = 0.0
        paid = 0.0

        if len(mr) > 2:
            for receipt in mr[:-1]:
                advance += receipt.amount
            paid = mr[-1].amount
        elif len(mr) == 2:
            advance += mr[0].amount
            paid += mr[1].amount
        elif len(mr) == 1:
            advance += mr[0].amount

        return {
            "advance": advance,
            "paid": paid,
        }

    def calculate_bill(self):
        self.ensure_one()

        bill_registers = self.env["bill.register"].search([
            ("general_admission_id", "=", self.id),
            ("state", "=", "confirmed"),
        ])

        hospital_bill_line_obj = self.env["hospital.bill.line"]
        investigation_paid = 0.0
        investigation_total = 0.0
        last_bill_line = False

        for bill in bill_registers:
            
            
            if bill.is_applied_to_admission == False:
                investigation_paid += bill.paid
                

                for item in bill.bill_register_line_id:
                    existing_item = hospital_bill_line_obj.search([
                        ("item_name", "=", item.name.id),
                        ("bill_created_date", "=", item.create_date),
                        ("hospital_admission_id", "=", self.id),
                    ], limit=1)

                    if not existing_item:
                        last_bill_line = hospital_bill_line_obj.create({
                            "item_name": item.name.id,
                            "product_qty": 1,
                            "price": item.price,
                            "discount": item.discount,
                            "total_discount": item.total_discount,
                            "total_amount": item.total_amount,
                            "bill_created_date": item.create_date,
                            "hospital_admission_id": self.id,
                        })
                        investigation_total += item.total_amount
                    else:
                        last_bill_line = existing_item

                bill.is_applied_to_admission = True

        self.investigation_total += investigation_total
        self.investigation_paid += investigation_paid
        self._onchange_paid()

        return last_bill_line.id if last_bill_line else True

    def btn_final_settlement(self):
        for rec in self:
            if rec.state not in ("activated", "released"):
                raise UserError(_("Please confirm the admission before releasing it."))
            if rec.due > 0:
                raise UserError(_("Please Pay the Due Bill"))
            if not rec.release_note:
                raise UserError(_("Please give the description about the release note field"))
            if rec.state == "activated":
                rec.state = "released"
        return True

    def hospital_change_status(self):
        for rec in self:
            if rec.state in ("activated", "released"):
                raise UserError(_("Already this Bill is Confirmed."))
            rec.state = "activated"

            # No admission report is defined in this module yet, so this
            # resolves to nothing and the status change proceeds without a
            # printout. Define a 'general_report_admission' report to enable it.
            report_action = self.env.ref(
                "leih19.general_report_admission",
                raise_if_not_found=False,
            )
            if report_action:
                return report_action.report_action(rec)
        return True

    def admission_cancel(self):
        for rec in self:
            moves = self.env["account.move"].search([("ref", "=", rec.name)])
            if moves:
                for move in moves:
                    try:
                        if move.state == "posted":
                            move.button_draft()
                    except Exception:
                        pass
                moves.unlink()

            rec.state = "cancelled"

            receipts = self.env["leih.money.receipt"].search([
                ("general_admission_id", "=", rec.id)
            ])
            if receipts:
                receipts.write({"state": "cancel"})

        return True

    def add_new_test(self):
        self.ensure_one()
        view = self.env.ref("leih19.add_bill_form_view", raise_if_not_found=False)
        if not view:
            raise UserError(_("The form view 'add_bill_view' was not found."))

        return {
            "name": _("Pay Invoice"),
            "view_mode": "form",
            "view_id": view.id,
            "res_model": "add.bill",
            "type": "ir.actions.act_window",
            "target": "new",
            "domain": [],
            "context": {
                "leih_admission_id": self.id,
            },
        }

    def btn_pay(self):
        self.ensure_one()

        if self.state in ("pending", "cancelled"):
            raise UserError(_("Please Confirm and Print the Bill"))


        return {
            "name": _("Payment Invoice"),
            "type": "ir.actions.act_window",
            "res_model": "hospital.admission.payment",
            "view_mode": "form",
            # "view_id": view.id,
            "target": "new",
            "context": {
                "default_admission_id": self.id,
                'default_date': fields.Date.context_today(self),
                "default_amount": self.due,
                'default_payment_type': self.payment_type.id if self.payment_type else False,
            },
    }
    def add_discount(self):
        self.ensure_one()
        view = self.env.ref("leih19.discount_form_view", raise_if_not_found=False)
        if not view:
            raise UserError(_("The discount form view was not found."))

        return {
            "name": _("Pay Invoice"),
            "view_mode": "form",
            "view_id": view.id,
            "res_model": "discount",
            "type": "ir.actions.act_window",
            "target": "new",
            "domain": [],
            "context": {
                "pi_id": self.id,
            },
        }

    def btn_bill(self):
        self.ensure_one()
        return self.calculate_bill()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for rec in records:
            # Note: due may be negative when an advance deposit exceeds current
            # charges (a credit balance) -- that is valid for IPD admissions.
            if rec.name == "New":
                prefix = "E-0" if rec.emergency else "HA-0"
                rec.name = f"{prefix}{rec.id}"

        return records

