from odoo import api, fields, models, _
from odoo.addons.leih19.models.appointment_booking import SEX_SELECTION
from odoo.exceptions import UserError


class AppointmentArrivalWizard(models.TransientModel):
    """The arrival desk, in one screen.

    Three things happen at once when a patient reports, and they are on one form
    because they are one conversation across the counter:

    1. the identity captured at the serial desk is checked and completed;
    2. an existing patient is matched, or a new hospital record is registered;
    3. the consultation fee is taken.

    Step 2 is the reason this is a wizard rather than a button. A patient who has
    been to this hospital before must *not* get a second hospital number, and the
    only person who can tell "Rahim Uddin, 01712345678" from "Rahim U.,
    01712345678" is the one looking at the patient. So the matches are put in
    front of them and they choose, instead of the code guessing.
    """
    _name = 'appointment.arrival.wizard'
    _description = 'Register Patient Arrival'

    appointment_id = fields.Many2one(
        'appointment.booking', string='Appointment', required=True,
        ondelete='cascade', readonly=True)
    doctor_name = fields.Many2one(related='appointment_id.doctor_name', readonly=True)
    serial_no = fields.Integer(related='appointment_id.serial_no', readonly=True)
    token_no = fields.Integer(related='appointment_id.token_no', readonly=True)

    # --- identity: seeded from the booking, completed here ---
    # Not required at the model level: on a TransientModel that becomes a NOT
    # NULL column, which turns "the desk has not typed it yet" into a database
    # error instead of a field outlined in red. The form marks them required and
    # action_confirm re-checks, which is where a readable message belongs.
    patient_name = fields.Char('Patient Name')
    age = fields.Char('Age')
    date_of_birth = fields.Date('Date of Birth')
    sex = fields.Selection(SEX_SELECTION, string='Sex', default='male', required=True)
    mobile = fields.Char('Mobile No')
    # patient.info marks address NOT NULL, and it is exactly the sort of thing
    # nobody dictates over a phone booking -- which is why it is collected here.
    address = fields.Char('Address')
    photo = fields.Image('Photo', max_width=1024, max_height=1024)

    mode = fields.Selection([
        ('new', 'Register a new patient'),
        ('existing', 'Use an existing patient record'),
    ], string='Patient Record', default='new', required=True)
    patient_id = fields.Many2one(
        'patient.info', string='Existing Patient',
        help='Search by name, mobile or patient id.')
    match_ids = fields.Many2many(
        'patient.info', string='Possible Matches', compute='_compute_match_ids')
    match_count = fields.Integer(compute='_compute_match_ids')

    # --- the fee ---
    amount = fields.Float('Consultation Fee')
    payment_note = fields.Char('Payment Note')

    print_id_card = fields.Boolean(
        'Print ID Card', default=False,
        help='Tick to print the hospital ID card straight after confirming. '
             'Off by default: the desk confirms the arrival and sends the '
             'patient to the doctor, and the card is printed on demand from '
             'the appointment\'s "Print ID Card" button whenever it is '
             'actually wanted.')

    @api.model
    def default_get(self, fields_list):
        """Seed the form from the booking the desk is standing on."""
        res = super().default_get(fields_list)
        booking = self.env['appointment.booking'].browse(
            res.get('appointment_id') or self.env.context.get('default_appointment_id'))
        if not booking.exists():
            return res
        res.update({
            'appointment_id': booking.id,
            'patient_name': booking.patient_name,
            'age': booking.age,
            'date_of_birth': booking.date_of_birth,
            'mobile': booking.phone,
            'address': booking.address,
            # The booking's amount is only filled by an onchange, so a serial
            # taken any other way (imported, created by code, saved before the
            # doctor was picked) arrives here as zero. Fall back to the session
            # fee and then the doctor's own, so the desk is never quietly asked
            # to collect nothing.
            'amount': (booking.amount
                       or booking.schedule_id.consultation_fee
                       or booking.doctor_name.ipd_visit),
        })
        if booking.sex:
            # Same selection on both sides now -- straight copy.
            res['sex'] = booking.sex
        if booking.patient_id:
            # A returning patient the desk already identified at booking time.
            res.update({'mode': 'existing', 'patient_id': booking.patient_id.id})
        return res

    @api.depends('mobile', 'patient_name')
    def _compute_match_ids(self):
        """Patients who might already be this person.

        Mobile first because it is the one thing said the same way twice; the
        name is only used when it is long enough not to match half the register.
        """
        Patient = self.env['patient.info']
        for rec in self:
            domain = []
            if rec.mobile and len(rec.mobile.strip()) >= 6:
                domain.append(('mobile', '=', rec.mobile.strip()))
            if rec.patient_name and len(rec.patient_name.strip()) >= 4:
                domain.append(('name', 'ilike', rec.patient_name.strip()))
            if not domain:
                rec.match_ids = rec.match_count = False
                continue
            if len(domain) > 1:
                domain = ['|'] + domain
            matches = Patient.search(domain, limit=10)
            rec.match_ids = matches
            rec.match_count = len(matches)

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        """Choosing an existing record pulls its details in, blanks aside."""
        patient = self.patient_id
        if not patient:
            return
        self.mode = 'existing'
        self.patient_name = patient.name
        self.age = patient.age or self.age
        self.sex = patient.sex or self.sex
        self.mobile = patient.mobile or self.mobile
        self.address = patient.address or self.address
        self.date_of_birth = patient.date_of_birth or self.date_of_birth

    # ------------------------------------------------------------------
    def _patient_vals(self):
        self.ensure_one()
        return {
            'name': self.patient_name,
            'age': self.age or False,
            'date_of_birth': self.date_of_birth or False,
            'sex': self.sex,
            'mobile': self.mobile or False,
            'address': self.address,
            'photo': self.photo or False,
        }

    def action_confirm(self):
        """Register the patient, mark the fee paid, put them in the queue."""
        self.ensure_one()
        booking = self.appointment_id
        if booking.status in ('arrived', 'in_consultation', 'converted'):
            raise UserError(_('This arrival has already been registered.'))
        missing = [label for value, label in (
            (self.patient_name, _('Patient Name')), (self.address, _('Address')))
            if not (value or '').strip()]
        if missing:
            raise UserError(_(
                'Complete the patient details before confirming: %s.',
                ', '.join(missing)))

        if self.mode == 'existing':
            patient = self.patient_id
            if not patient:
                raise UserError(_(
                    'Pick the existing patient record, or switch to '
                    '"Register a new patient".'))
            # Top up what the old record is missing. Never overwrite: the value
            # on file was verified once, what is typed here may be a mishearing.
            fill = {key: value for key, value in self._patient_vals().items()
                    if value and not patient[key]}
            if fill:
                patient.write(fill)
        else:
            patient = self.env['patient.info'].create(self._patient_vals())

        # A walk-in registered straight at the desk has no serial yet.
        if not booking.serial_no and booking.schedule_id:
            booking.action_confirm_serial()
        booking.action_allocate_token()

        booking.write({
            'patient_id': patient.id,
            'patient_name': patient.name,
            'age': self.age or booking.age,
            'sex': self.sex,
            'phone': self.mobile or booking.phone,
            'address': self.address,
            'date_of_birth': self.date_of_birth or booking.date_of_birth,
            'status': 'arrived',
            'arrived_on': fields.Datetime.now(),
            'amount': self.amount,
            'payment_done': True,
            'collected_by': self.env.user.id,
            'payment_note': self.payment_note or False,
        })

        if self.print_id_card:
            return self.env.ref(
                'leih19.action_report_patient_id_card').report_action(patient)
        return {'type': 'ir.actions.act_window_close'}
