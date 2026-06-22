from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AppointmentBooking(models.Model):
    """Pre-appointment (name + mobile only) -> arrival -> real patient + OPD bill.

    A pre-appointment needs nothing more than a name, a phone number and a
    doctor session. When the person actually shows up, ``action_register_arrival``
    promotes them into a real ``patient.info`` and opens an ``opd.ticket`` (the
    OPD bill) seeded with the consultation fee.
    """
    _inherit = 'appointment.booking'

    schedule_id = fields.Many2one(
        'doctor.schedule', string='Session',
        domain="[('doctor_id', '=', doctor_name)]")
    appointment_date = fields.Date('Appointment Date', default=fields.Date.context_today)
    serial_no = fields.Integer('Serial No', readonly=True, copy=False)

    patient_id = fields.Many2one(
        'patient.info', string='Patient', readonly=True, copy=False,
        help='The real patient record, created when the person arrives.')
    opd_ticket_id = fields.Many2one(
        'opd.ticket', string='OPD Ticket', readonly=True, copy=False)

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

    @api.onchange('schedule_id')
    def _onchange_schedule_id(self):
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

    def _prepare_patient_vals(self):
        self.ensure_one()
        sex = self.sex if self.sex in ('male', 'female', 'others') else 'male'
        return {
            'name': self.patient_name or 'Patient',
            'mobile': self.phone or False,
            'age': self.age or False,
            'sex': sex,
            'address': self.address or 'N/A',
        }

    def _create_opd_ticket(self):
        self.ensure_one()
        ticket = self.env['opd.ticket'].create({
            'name': self.patient_id.name,
            'patient_name': self.patient_id.id,
            'ref_doctors': self.doctor_name.id,
            'date': fields.Date.context_today(self),
        })
        entry = self.schedule_id.consultation_entry_id
        fee = self.schedule_id.consultation_fee or self.amount
        if entry and fee:
            self.env['opd.ticket.line'].create({
                'opd_ticket_id': ticket.id,
                'name': entry.id,
                'department': self.doctor_name.department or False,
                'price': fee,
                'total_amount': fee,
            })
            ticket.total = fee
        return ticket

    def action_register_arrival(self):
        """Promote a pre-appointment into a real patient + OPD bill."""
        self.ensure_one()
        if not self.doctor_name:
            raise UserError(_('Please select a doctor first.'))
        if not self.patient_id:
            self.patient_id = self.env['patient.info'].create(
                self._prepare_patient_vals())
        if not self.opd_ticket_id:
            self.opd_ticket_id = self._create_opd_ticket()
        self.status = 'arrived'
        return {
            'type': 'ir.actions.act_window',
            'name': _('OPD Ticket'),
            'res_model': 'opd.ticket',
            'view_mode': 'form',
            'res_id': self.opd_ticket_id.id,
            'target': 'current',
        }

    def action_open_opd_ticket(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'opd.ticket',
            'view_mode': 'form',
            'res_id': self.opd_ticket_id.id,
            'target': 'current',
        }
