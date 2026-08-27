from odoo import api, fields, models


class DoctorSchedule(models.Model):
    """A doctor's standard, recurring session.

    Bookings against a session get a running *serial number* (token) for the
    chosen date rather than a fixed clock time. ``capacity`` caps how many
    serials a session can issue per day.
    """
    _name = 'doctor.schedule'
    _description = 'Doctor Schedule / Session'
    _order = 'doctor_id, start_time'

    name = fields.Char('Session', required=True, help='e.g. Morning, Evening')
    doctor_id = fields.Many2one(
        'doctors.profile', string='Doctor', required=True, ondelete='cascade')
    active = fields.Boolean(default=True)

    # Recurring weekdays the session runs on (Python date.weekday(): Mon=0..Sun=6)
    mon = fields.Boolean('Mon')
    tue = fields.Boolean('Tue')
    wed = fields.Boolean('Wed')
    thu = fields.Boolean('Thu')
    fri = fields.Boolean('Fri')
    sat = fields.Boolean('Sat')
    sun = fields.Boolean('Sun')

    start_time = fields.Float('Start Time', help='24h, e.g. 17.0 = 5:00 PM')
    end_time = fields.Float('End Time')
    capacity = fields.Integer('Capacity (max serials/day)', default=20)
    consultation_fee = fields.Float('Consultation Fee')
    room_location = fields.Char(
        'Room / Location',
        help='Where this session is held - wing, floor and room number, e.g. '
             '"Extension Wing-2, 10th Floor-EW2, 1018". Printed on the '
             'consultation token so the patient knows where to go.')
    consultation_entry_id = fields.Many2one(
        'opd.ticket.entry', string='Consultation Item',
        help='OPD billing item used for the consultation line created when a '
             'patient arrives. Its account is reused; price comes from '
             '"Consultation Fee".')

    @api.depends('name', 'doctor_id', 'doctor_id.name')
    def _compute_display_name(self):
        for rec in self:
            doctor = rec.doctor_id.name or ''
            rec.display_name = f'{doctor} - {rec.name}' if rec.name else doctor

    def weekday_open(self, weekday):
        """True if this session runs on the given Python weekday (Mon=0..Sun=6)."""
        self.ensure_one()
        return [self.mon, self.tue, self.wed, self.thu,
                self.fri, self.sat, self.sun][weekday]
