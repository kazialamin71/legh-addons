import base64

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Python's date.weekday(): Mon=0 .. Sun=6. Same order as doctor.schedule's
# mon..sun booleans, which is what weekday_open() indexes into.
WEEKDAY_FIELDS = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
WEEKDAY_LABELS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday',
                  'Friday', 'Saturday', 'Sunday')


class AppointmentBooking(models.Model):
    """A serial (token) taken against a doctor session.

    Deliberately split into two desks, because that is how an OPD actually runs:

    * **Serial desk** - takes the bare minimum (doctor, session, date, name, age,
      mobile), issues the serial and prints the token. It creates **no** patient
      record: most of what it captures is shouted across a counter or taken over
      the phone, and half of those people never turn up.
    * **Arrival desk** - the patient is standing there, so the rest of the
      identity (address, photo, gender, date of birth) can be taken properly.
      Only now is a ``patient.info`` created, which is what mints the hospital
      number and lets the ID card print.

    Consultation money is recorded here and is **not** accounting: registering an
    arrival is what marks the fee paid. There is no journal entry, no invoice and
    no bill.register behind it - ``amount`` is simply what was handed over, and
    ``collected_by`` / ``arrived_on`` say who took it and when, which is all a
    day-end cash count needs.
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
        'patient.info', string='Patient', copy=False, index=True, readonly=True,
        help='The hospital patient record. Empty until the patient turns up and '
             'the arrival desk registers them.')

    # patient_name / age / sex / phone / address stay the plain, typed fields the
    # base module defines. They were briefly turned into read-only mirrors of
    # patient_id, which forced the serial desk to create a patient record before
    # it could take a booking -- the exact opposite of how the counter works.
    #
    # required=False on purpose: the base model marks patient_name and age NOT
    # NULL, and re-imposing that on a table that already holds rows without them
    # fails the upgrade. What is actually required is enforced on the form.
    patient_name = fields.Char(required=False)
    age = fields.Char(required=False)

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        """Picking a known patient fills the identity fields in for the desk."""
        patient = self.patient_id
        if not patient:
            return
        self.patient_name = patient.name
        self.age = patient.age or self.age
        # appointment.booking and patient.info share one selection, so this is a
        # straight copy -- it used to have to go through the labels.
        self.sex = patient.sex or self.sex
        self.phone = patient.mobile or self.phone
        self.address = patient.address or self.address
        if patient.date_of_birth and not self.date_of_birth:
            self.date_of_birth = patient.date_of_birth

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

    schedule_warning = fields.Char(
        'Schedule Warning', compute='_compute_schedule_warning',
        help='Set when the appointment date is not a day the chosen session '
             'runs on. A warning only -- the booking is never blocked.')

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

    # ------------------------------------------------------------------
    # Session / weekday check
    #
    # A warning, deliberately never a block. Doctors do see patients on their
    # day off -- a referral, a post-op check, someone who travelled in -- and a
    # desk that cannot take that booking just writes it on paper instead, which
    # is worse than a booking the system knows is off-schedule.
    # ------------------------------------------------------------------
    def _schedule_mismatch_message(self):
        """Why this date is wrong for this session, or '' when it is fine."""
        self.ensure_one()
        schedule = self.schedule_id
        day = self.appointment_date
        if not schedule or not day:
            return ''
        if schedule.weekday_open(day.weekday()):
            return ''
        open_days = [label for label, fname in zip(WEEKDAY_LABELS, WEEKDAY_FIELDS)
                     if schedule[fname]]
        doctor = schedule.doctor_id.name or _('This doctor')
        if open_days:
            return _(
                '%(doctor)s does not sit on %(weekday)s. The "%(session)s" '
                'session runs on %(open_days)s. You can still take this serial '
                'if the patient wants it - nothing is blocked.',
                doctor=doctor, weekday=WEEKDAY_LABELS[day.weekday()],
                session=schedule.name, open_days=', '.join(open_days))
        return _(
            'The "%(session)s" session has no weekdays ticked at all, so every '
            'date is off-schedule. Set the days on the doctor session to stop '
            'this warning.', session=schedule.name)

    @api.depends('schedule_id', 'appointment_date',
                 'schedule_id.mon', 'schedule_id.tue', 'schedule_id.wed',
                 'schedule_id.thu', 'schedule_id.fri', 'schedule_id.sat',
                 'schedule_id.sun')
    def _compute_schedule_warning(self):
        for rec in self:
            rec.schedule_warning = rec._schedule_mismatch_message()

    @api.onchange('schedule_id', 'appointment_date')
    def _onchange_schedule_weekday(self):
        """Put the off-day in front of the desk while they are still booking.

        The computed banner stays on the form; this is the one-shot dialog that
        makes sure it is not simply scrolled past.
        """
        message = self._schedule_mismatch_message()
        if message:
            return {'warning': {'title': _('Doctor not scheduled that day'),
                                'message': message}}

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

    # selection_add both appends the new states and relabels the ones already
    # there ("Pending" -> "Booked"), because a value already in the base list is
    # re-labelled rather than duplicated. The base's 'reached' and 'paid' are
    # left alone: nothing sets them any more, but rows still carrying them load.
    status = fields.Selection(
        selection_add=[
            ('pending', 'Booked'),
            ('arrived', 'Arrived / Paid'),
            ('in_consultation', 'With Doctor'),
            ('converted', 'Completed'),
        ],
        ondelete={'arrived': 'set default',
                  'in_consultation': 'set default',
                  'converted': 'set default'},
        index=True, copy=False)

    # ------------------------------------------------------------------
    # Consultation fee -- recorded, not accounted for
    #
    # Registering the arrival *is* the payment: the patient hands the fee over
    # at the desk and walks to the doctor. These three fields are the whole
    # record of it, which is enough to reconcile a cash drawer at the end of the
    # day and nothing more. Anything that has to hit the books goes through
    # Bill Register or POS, not through here.
    # ------------------------------------------------------------------
    arrived_on = fields.Datetime(
        'Arrived On', readonly=True, copy=False,
        help='When the patient reported at the desk and paid. Also what the '
             "doctor's queue is ordered by.")
    collected_by = fields.Many2one(
        'res.users', string='Fee Collected By', readonly=True, copy=False)
    payment_note = fields.Char(
        'Payment Note', copy=False,
        help='Free text for the desk, e.g. "waived", "staff rate", "bKash".')

    waiting_time = fields.Char(
        'Waiting', compute='_compute_waiting_time',
        help='How long this patient has been waiting since they reported.')

    prescription_ids = fields.One2many(
        'doctor.prescription', 'appointment_id', string='Prescriptions')
    prescription_count = fields.Integer(compute='_compute_prescription_count')

    @api.depends('arrived_on', 'status')
    def _compute_waiting_time(self):
        now = fields.Datetime.now()
        for rec in self:
            if not rec.arrived_on or rec.status not in ('arrived', 'in_consultation'):
                rec.waiting_time = ''
                continue
            minutes = int((now - rec.arrived_on).total_seconds() // 60)
            rec.waiting_time = (
                '%d min' % minutes if minutes < 60
                else '%dh %02dm' % divmod(minutes, 60))

    @api.depends('prescription_ids')
    def _compute_prescription_count(self):
        for rec in self:
            rec.prescription_count = len(rec.prescription_ids)

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
        """Open the arrival desk wizard.

        The wizard is where the identity is completed (address, photo, gender,
        date of birth), an existing patient is matched or a new one registered,
        and the fee is taken. It writes back here on confirm.
        """
        self.ensure_one()
        if not self.doctor_name:
            raise UserError(_('Please select a doctor first.'))
        if self.status in ('arrived', 'in_consultation', 'converted'):
            raise UserError(_(
                '%(patient)s has already been registered as arrived.',
                patient=self.patient_name or self.name))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Register Arrival'),
            'res_model': 'appointment.arrival.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_appointment_id': self.id},
        }

    def action_start_consultation(self):
        """Take the patient out of the queue and open their prescription.

        Reuses a prescription already written for this visit rather than opening
        a second one, so a doctor who closes the tab and clicks again lands back
        on what they were writing.
        """
        self.ensure_one()
        if not self.patient_id:
            raise UserError(_(
                'Register this patient\'s arrival before starting the '
                'consultation - there is no patient record yet.'))
        prescription = self.prescription_ids[:1]
        if not prescription:
            prescription = self.env['doctor.prescription'].create({
                'patient_id': self.patient_id.id,
                'doctor_id': self.doctor_name.id,
                'department': self.doctor_name.department,
                'source_model': 'appointment.booking',
                'appointment_id': self.id,
            })
        if self.status == 'arrived':
            self.status = 'in_consultation'
        return {
            'type': 'ir.actions.act_window',
            'name': _('Prescription'),
            'res_model': 'doctor.prescription',
            'view_mode': 'form',
            'res_id': prescription.id,
            'target': 'current',
        }

    def action_complete_consultation(self):
        """Doctor is done: drop the patient off the queue."""
        self.filtered(lambda r: r.status in ('arrived', 'in_consultation')).status = 'converted'
        return True

    def action_view_prescriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Prescriptions'),
            'res_model': 'doctor.prescription',
            'view_mode': 'list,form',
            'domain': [('appointment_id', '=', self.id)],
            'context': {
                'default_appointment_id': self.id,
                'default_patient_id': self.patient_id.id,
                'default_doctor_id': self.doctor_name.id,
                'default_source_model': 'appointment.booking',
            },
        }

    def action_print_id_card(self):
        """Print the hospital ID card for the patient registered at arrival."""
        self.ensure_one()
        if not self.patient_id:
            raise UserError(_(
                'There is no patient record yet - register the arrival first.'))
        return self.env.ref(
            'leih19.action_report_patient_id_card').report_action(self.patient_id)

    def action_open_opd_ticket(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'opd.ticket',
            'view_mode': 'form',
            'res_id': self.opd_ticket_id.id,
            'target': 'current',
        }
