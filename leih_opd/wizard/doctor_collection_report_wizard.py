from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DoctorCollectionReportWizard(models.TransientModel):
    """Doctor-wise consultation collection over a date range.

    Reads ``appointment.booking`` directly rather than the money receipts the
    other collection reports are built on, because consultation money never
    becomes a receipt: registering the arrival *is* the payment (see
    ``appointment.arrival.wizard``). ``arrived_on`` is therefore the date the
    money changed hands, and it is what the range filters on -- not the
    appointment date, which for a booking taken last week says nothing about
    when the cash arrived.
    """
    _name = 'appointment.doctor.collection.wizard'
    _description = 'Doctor-wise Collection Report'

    date_from = fields.Date(
        'From Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(
        'To Date', required=True, default=fields.Date.context_today)
    doctor_ids = fields.Many2many(
        'doctors.profile', string='Doctors',
        help='Leave empty to report on every doctor who collected in the period.')
    include_detail = fields.Boolean(
        'List Each Patient', default=False,
        help='Print the individual visits under each doctor, not just the totals.')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from > rec.date_to:
                raise UserError(_('"From Date" is after "To Date".'))

    def _booking_domain(self):
        """Paid consultations whose money was taken inside the period."""
        self.ensure_one()
        domain = [
            ('payment_done', '=', True),
            ('arrived_on', '>=', fields.Datetime.to_datetime(self.date_from)),
            # arrived_on is a datetime, so the closing day needs its whole span;
            # comparing against the bare date would drop everyone after midnight.
            ('arrived_on', '<', fields.Datetime.to_datetime(
                fields.Date.add(self.date_to, days=1))),
        ]
        if self.doctor_ids:
            domain.append(('doctor_name', 'in', self.doctor_ids.ids))
        return domain

    def _collect(self):
        """Per-doctor totals, ready for the template.

        Patients and visits are counted separately on purpose: someone who comes
        back twice in the period is one patient but two consultations, and a
        doctor's payment is owed on the consultations.
        """
        self.ensure_one()
        bookings = self.env['appointment.booking'].search(
            self._booking_domain(), order='doctor_name, arrived_on')

        groups = {}
        for booking in bookings:
            doctor = booking.doctor_name
            group = groups.setdefault(doctor.id, {
                'doctor': doctor,
                'visits': 0,
                'patients': set(),
                'total': 0.0,
                'bookings': self.env['appointment.booking'],
            })
            group['visits'] += 1
            # Fall back to the typed name for a visit registered before the
            # patient record existed, so nobody is silently dropped from the count.
            group['patients'].add(
                booking.patient_id.id or ('name:%s' % (booking.patient_name or booking.id)))
            group['total'] += booking.amount or 0.0
            group['bookings'] |= booking

        rows = sorted(groups.values(), key=lambda g: g['doctor'].name or '')
        for row in rows:
            row['patients'] = len(row['patients'])
        return rows

    def action_print(self):
        self.ensure_one()
        if not self._collect():
            raise UserError(_(
                'No consultation money was collected between %(start)s and '
                '%(end)s for the selected doctors.',
                start=self.date_from, end=self.date_to))
        return self.env.ref(
            'leih_opd.action_report_doctor_collection').report_action(self)

    def action_open_list(self):
        """The same figures on screen, for anyone who wants to drill in."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Consultation Collections'),
            'res_model': 'appointment.booking',
            'view_mode': 'list,form',
            'domain': self._booking_domain(),
            'context': {'search_default_group_doctor': 1},
        }
