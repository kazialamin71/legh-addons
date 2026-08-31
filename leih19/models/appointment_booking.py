from odoo import api, fields, models

# Shared with patient.info so the two can be mapped onto each other without a
# label lookup in between.
SEX_SELECTION = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('others', 'Others'),
]


class AppointmentBooking(models.Model):
    _name = 'appointment.booking'
    _description = 'AppointmentBooking'

    # Allocated from a sequence in create(). readonly so the desk cannot type
    # over it, copy=False so duplicating a booking mints a fresh number instead
    # of carrying the old one across.
    name = fields.Char('Appointment', readonly=True, copy=False)
    patient_name = fields.Char('Patient Name', required=True)
    age = fields.Char('Age', required=True)
    # A selection rather than free text: the desk used to type "M", "male",
    # "Male " and everything in between, which left the field impossible to
    # filter or group on and forced every consumer to guess at the spelling.
    sex = fields.Selection(SEX_SELECTION, string='Sex')
    phone = fields.Char('Mobile No.')
    address = fields.Char('Address')
    doctor_name = fields.Many2one('doctors.profile', string='Doctor Name')
    # Time of day as hours since midnight -- Odoo has no time-of-day field, and
    # a float behind the `float_time` widget is how the standard modules model
    # one (hr.attendance, resource.calendar). The widget shows and parses HH:MM,
    # so the desk types a clock time and the value stays sortable and filterable.
    time = fields.Float('Time')
    time_display = fields.Char(
        'Time (printed)', compute='_compute_time_display',
        help='The appointment time as it prints on slips and tokens.')
    date = fields.Date('Date')
    status = fields.Selection([('pending', 'Pending'), ('reached', 'Reached'), ('paid', 'Paid')], string='Status', default='pending')
    patient_status = fields.Selection([('new', 'New Patient'), ('review', 'Review')], string='Patient Status')
    amount = fields.Float('amount')
    payment_done = fields.Boolean('Payment', default=False)

    @api.depends('time')
    def _compute_time_display(self):
        """Render `time` as a 12-hour clock time for print.

        0.0 counts as "not set": a Float column has no NULL to distinguish an
        unset time from midnight, and midnight is not a time an OPD books.
        """
        for rec in self:
            if not rec.time:
                rec.time_display = ''
                continue
            hours, minutes = divmod(int(round(rec.time * 60)), 60)
            hours %= 24
            rec.time_display = '%d:%02d %s' % (
                hours % 12 or 12, minutes, 'AM' if hours < 12 else 'PM')
