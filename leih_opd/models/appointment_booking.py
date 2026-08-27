import base64

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AppointmentBooking(models.Model):
    """Appointment against a doctor session, for a patient already on file.

    The patient is picked from ``patient.info`` the same way the Bill Register
    picks one -- searching by name, mobile or patient id -- and is registered
    through the patient form when they are genuinely new. Arrival simply marks
    the appointment as arrived; it creates neither a patient nor a bill.
    """
    _inherit = 'appointment.booking'
    # Newest appointment first: reception works off the top of the list.
    _order = 'id desc'

    schedule_id = fields.Many2one(
        'doctor.schedule', string='Session',
        domain="[('doctor_id', '=', doctor_name)]")
    appointment_date = fields.Date('Appointment Date', default=fields.Date.context_today)
    serial_no = fields.Integer('Serial No', readonly=True, copy=False)

    patient_id = fields.Many2one(
        'patient.info', string='Patient', copy=False, index=True,
        help='Search an existing patient by name, mobile or patient id. '
             'Use "Create and edit..." to register someone genuinely new.')

    # Patient details mirror the selected patient, exactly like the Bill
    # Register form. They used to be typed by hand with no link to
    # patient.info, which is what made arrival register a second patient
    # record for someone already on the list.
    # required=False on purpose: a stored compute is filled *after* the INSERT,
    # so leaving the base NOT NULL in place makes every create fail. What is
    # actually required is the patient, enforced on the form.
    patient_name = fields.Char(
        compute='_compute_patient_details', store=True, readonly=True,
        required=False)
    age = fields.Char(
        compute='_compute_patient_details', store=True, readonly=True,
        required=False)
    sex = fields.Char(compute='_compute_patient_details', store=True, readonly=True)
    phone = fields.Char(compute='_compute_patient_details', store=True, readonly=True)
    address = fields.Char(compute='_compute_patient_details', store=True, readonly=True)

    @api.depends('patient_id')
    def _compute_patient_details(self):
        sex_labels = dict(self.env['patient.info']._fields['sex'].selection)
        for rec in self:
            patient = rec.patient_id
            if not patient:
                # Pre-existing bookings captured before patients were linked
                # keep whatever was typed on them.
                rec.patient_name = rec.patient_name
                rec.age = rec.age
                rec.sex = rec.sex
                rec.phone = rec.phone
                rec.address = rec.address
                continue
            rec.patient_name = patient.name
            rec.age = patient.age or False
            rec.sex = sex_labels.get(patient.sex, patient.sex) or False
            rec.phone = patient.mobile or False
            rec.address = patient.address or False
    opd_ticket_id = fields.Many2one(
        'opd.ticket', string='OPD Ticket', readonly=True, copy=False)

    # ------------------------------------------------------------------
    # Consultation token identifiers
    #
    # Three different numbers, deliberately kept apart because they answer
    # three different questions:
    #   HN     - who is this person, for life (the patient code)
    #   CN     - which consultation is this, for ever (never reused)
    #   Token  - what is their place in today's queue (restarts each day)
    # `serial_no` stays what it always was: the serial inside one doctor
    # session, printed as "SL" on the slip.
    # ------------------------------------------------------------------
    cn_number = fields.Char(
        'CN (Consultation No.)', readonly=True, copy=False, index=True,
        help='Consultation number, allocated once per visit and never reused. '
             'Printed and barcoded on the consultation token.')
    cn_date = fields.Date(
        'CN Date', readonly=True, copy=False,
        help='Date the consultation number was issued.')
    vn_date = fields.Date(
        'VN Date', copy=False,
        help='Visit date the token is valid for. Defaults to the appointment date.')
    token_no = fields.Integer(
        'Token No.', readonly=True, copy=False, index=True,
        help='Position in the day queue. Restarts at 1 every day, across the '
             'whole hospital.')
    token_date = fields.Date(
        'Token Date', readonly=True, copy=False,
        help='The day this token belongs to - what the daily counter resets on.')

    hn_number = fields.Char(
        'HN (Hospital No.)', compute='_compute_hn_number', store=True,
        help="The patient's permanent hospital number. Blank until the "
             'pre-appointment is promoted to a real patient record.')

    date_of_birth = fields.Date(
        'Date of Birth',
        help='Taken from the patient record when there is one; can be captured '
             'here for a pre-appointment that has no patient yet.')
    age_display = fields.Char(
        'Age (Y/M/D)', compute='_compute_age_display',
        help='Exact age as Years / Months / Days, the way it prints on the token.')

    location = fields.Char(
        'Location', compute='_compute_location', store=True, readonly=False,
        help='Where the patient should go - wing, floor and room. Seeded from '
             'the doctor session, overridable per appointment.')

    token_printed_on = fields.Datetime(
        'Token Last Printed', readonly=True, copy=False,
        help='Stamped every time the token is printed, so a reprint is visible.')

    @api.depends('patient_id.patient_id')
    def _compute_hn_number(self):
        for rec in self:
            rec.hn_number = rec.patient_id.patient_id or False

    @api.depends('date_of_birth', 'patient_id.date_of_birth', 'age')
    def _compute_age_display(self):
        """Y / M / D from the date of birth, falling back to the free-text age.

        Paediatric slips are the reason this is not just a year count: "6 Y 2 M
        18 D" is clinically meaningful for a child, "6" is not.
        """
        today = fields.Date.context_today(self)
        for rec in self:
            dob = rec.date_of_birth or rec.patient_id.date_of_birth
            if not dob:
                rec.age_display = rec.age or ''
                continue
            delta = relativedelta(today, dob)
            rec.age_display = '%s Y %s M %s D' % (delta.years, delta.months, delta.days)

    @api.depends('schedule_id.room_location')
    def _compute_location(self):
        for rec in self:
            if rec.schedule_id.room_location:
                rec.location = rec.schedule_id.room_location

    @api.onchange('patient_id')
    def _onchange_patient_dob(self):
        if self.patient_id.date_of_birth and not self.date_of_birth:
            self.date_of_birth = self.patient_id.date_of_birth

    # ------------------------------------------------------------------
    # Number allocation
    # ------------------------------------------------------------------
    def _next_token_no(self, day):
        """Next free token for `day`.

        Read off the highest token already issued that day rather than a
        sequence, so the counter restarts on its own each morning with no cron
        and no reset step anyone can forget.
        """
        self.ensure_one()
        last = self.search([('token_date', '=', day), ('token_no', '!=', 0)],
                           order='token_no desc', limit=1)
        return (last.token_no or 0) + 1

    def action_allocate_token(self):
        """Give this appointment its CN and its token for the day.

        Idempotent: an appointment that already has both is left alone, so
        pressing Print twice does not burn two numbers.
        """
        for rec in self:
            today = fields.Date.context_today(rec)
            if not rec.cn_number:
                rec.cn_number = self.env['ir.sequence'].next_by_code(
                    'appointment.consultation.number') or '/'
                rec.cn_date = today
            if not rec.token_no:
                day = rec.appointment_date or today
                rec.token_date = day
                rec.token_no = rec._next_token_no(day)
            if not rec.vn_date:
                rec.vn_date = rec.appointment_date or today
        return True

    def _barcode_data_uri(self, value, barcode_type='Code128',
                          width=600, height=100, humanreadable=False):
        """Render a barcode / QR code as an embedded data: URI.

        The usual `/report/barcode/...` src makes wkhtmltopdf take an HTTP round
        trip back into Odoo. This server hosts several databases with no
        db_filter set, so that unauthenticated request cannot resolve a database
        and answers 404 - and a 404 on an <img> prints as a silent empty box,
        not an error. Rendering the PNG here and inlining the bytes removes the
        round trip, so the token prints correctly regardless of how the server
        is addressed or whether it is reachable from the PDF engine at all.
        """
        if not value:
            return ''
        png = self.env['ir.actions.report'].barcode(
            barcode_type, value, width=width, height=height,
            humanreadable=humanreadable)
        return 'data:image/png;base64,%s' % base64.b64encode(png).decode()

    def action_print_token(self):
        """Allocate the numbers if needed, then print both POS slips."""
        self.ensure_one()
        if not self.doctor_name:
            raise UserError(_('Please select a doctor before printing the token.'))
        self.action_allocate_token()
        self.token_printed_on = fields.Datetime.now()
        return self.env.ref('leih_opd.action_report_appointment_token').report_action(self)

    status = fields.Selection(
        selection_add=[('arrived', 'Arrived'), ('converted', 'Converted')],
        ondelete={'arrived': 'set default', 'converted': 'set default'})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'appointment.booking') or '/'
        return super().create(vals_list)

    @api.onchange('doctor_name')
    def _onchange_doctor_fee(self):
        """Picking the doctor proposes their visit fee as the amount."""
        for rec in self:
            if rec.doctor_name:
                rec.amount = rec.doctor_name.ipd_visit

    @api.onchange('schedule_id')
    def _onchange_schedule_id(self):
        # Only when the doctor has no fee on file, so a session-specific fee
        # still gets a chance to fill an otherwise empty amount.
        if self.schedule_id and not self.amount:
            self.amount = self.schedule_id.consultation_fee

    def _booked_serials(self):
        """How many serials are already issued for this session + date."""
        self.ensure_one()
        return self.search_count([
            ('schedule_id', '=', self.schedule_id.id),
            ('appointment_date', '=', self.appointment_date),
            ('serial_no', '!=', 0),
            ('id', '!=', self.id),
        ])

    def action_confirm_serial(self):
        """Assign the next serial number, enforcing session capacity."""
        for rec in self:
            if not rec.schedule_id:
                raise UserError(_('Please choose a doctor session first.'))
            if not rec.appointment_date:
                raise UserError(_('Please set the appointment date.'))
            if rec.serial_no:
                continue
            booked = rec._booked_serials()
            capacity = rec.schedule_id.capacity
            if capacity and booked >= capacity:
                raise UserError(_(
                    'Session "%(session)s" on %(date)s is full (capacity %(cap)s).',
                    session=rec.schedule_id.display_name,
                    date=rec.appointment_date, cap=capacity))
            rec.serial_no = booked + 1
        return True

    def action_register_arrival(self):
        """Mark the appointment as arrived.

        Nothing is created here on purpose: the patient already exists (it is
        chosen on the form) and OPD billing is raised from the OPD Ticket /
        Bill Register screens, not from the appointment.
        """
        self.ensure_one()
        if not self.doctor_name:
            raise UserError(_('Please select a doctor first.'))
        if not self.patient_id:
            raise UserError(_(
                'Select the patient on this appointment before registering '
                'their arrival.'))
        self.status = 'arrived'
        return True

    def action_open_opd_ticket(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'opd.ticket',
            'view_mode': 'form',
            'res_id': self.opd_ticket_id.id,
            'target': 'current',
        }
