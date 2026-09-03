import logging
from collections import defaultdict

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

WEEKDAYS = ('Monday', 'Tuesday', 'Wednesday', 'Thursday',
            'Friday', 'Saturday', 'Sunday')


def _clock(value):
    """Hours-since-midnight as a 12-hour clock time, e.g. 17.5 -> "5:30 PM".

    Session times are stored as floats, so they need rendering before they can
    go in a text message; "17.5" would be meaningless to a patient.
    """
    if not value:
        return ''
    hours, minutes = divmod(int(round(float(value) * 60)), 60)
    hours %= 24
    return '%d:%02d %s' % (hours % 12 or 12, minutes, 'AM' if hours < 12 else 'PM')


class AppointmentBooking(models.Model):
    """Text the patient when their serial is confirmed."""
    _inherit = 'appointment.booking'

    sms_confirm_sent = fields.Boolean(
        'Confirmation Texted', readonly=True, copy=False,
        help='Set once the confirmation message has been handed to the gateway, '
             'so pressing Confirm again does not text the patient twice.')
    sms_message_ids = fields.One2many(
        'leih.sms.message', compute='_compute_sms_message_ids',
        string='Messages')
    sms_count = fields.Integer(compute='_compute_sms_message_ids')

    def _compute_sms_message_ids(self):
        Message = self.env['leih.sms.message']
        for rec in self:
            msgs = Message.search([('source_model', '=', 'appointment.booking'),
                                   ('source_res_id', '=', rec.id)])
            rec.sms_message_ids = msgs
            rec.sms_count = len(msgs)

    # ------------------------------------------------------------------
    def _sms_time(self):
        """The time to quote the patient.

        Their own appointment time when one was set; otherwise the session's
        window, because a serial system usually books a session rather than a
        clock time and "come at 5:00 PM - 9:00 PM" is still useful.
        """
        self.ensure_one()
        if self.time_display:
            return self.time_display
        sched = self.schedule_id
        start, end = _clock(sched.start_time), _clock(sched.end_time)
        if start and end:
            return '%s - %s' % (start, end)
        return start or ''

    def _sms_values(self):
        """Placeholder values for the message template."""
        self.ensure_one()
        date = self.appointment_date or self.date
        return {
            'patient': self.patient_name or '',
            'doctor': self.doctor_name.name or '',
            'date': date and date.strftime('%d-%m-%Y') or '',
            'day': date and WEEKDAYS[date.weekday()] or '',
            'time': self._sms_time(),
            'session': self.schedule_id.name or '',
            'serial': self.serial_no or '',
            'token': self.token_no or '',
            'fee': ('%.0f' % self.amount) if self.amount else '',
            'hn': self.hn_number or '',
            'hospital': self.env.company.name or '',
            'location': self.location or '',
        }

    def _sms_body(self, template):
        """Render the template, leaving unknown placeholders blank.

        format_map with a defaulting dict rather than format(): a typo in a
        template the desk edits must not raise in the middle of confirming a
        serial.
        """
        self.ensure_one()
        values = defaultdict(str, self._sms_values())
        try:
            return (template or '').format_map(values).strip()
        except Exception:  # noqa: BLE001 - a bad template must not stop a booking
            _logger.exception('Could not render the appointment SMS template')
            return ''

    def _send_confirmation_sms(self):
        cfg = self.env['leih.sms.config']._get()
        if not cfg.send_on_appointment_confirm:
            return
        for rec in self:
            if rec.sms_confirm_sent or not rec.phone:
                continue
            body = rec._sms_body(cfg.appointment_template)
            if not body:
                continue
            log = cfg.send_sms(rec.phone, body, source=rec)
            if log.state in ('sent', 'test'):
                rec.sms_confirm_sent = True

    def action_confirm_serial(self):
        """Confirm the serial, then tell the patient.

        The text is sent after the serial is assigned so the message can quote
        it, and it can never prevent the confirmation: send_sms does not raise,
        and a gateway failure only leaves a failed row in the message log.
        """
        res = super().action_confirm_serial()
        self._send_confirmation_sms()
        return res

    def action_view_sms(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Messages',
            'res_model': 'leih.sms.message',
            'view_mode': 'list,form',
            'domain': [('source_model', '=', 'appointment.booking'),
                       ('source_res_id', '=', self.id)],
        }
