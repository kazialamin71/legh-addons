import json
import logging
import re

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = 'http://202.72.233.114/api/v2/SendSMS'


class LeihSmsConfig(models.Model):
    """Gateway credentials and the one place a message is actually sent from.

    Credentials live here rather than in the source: they are per-installation,
    they get rotated, and a key in a git repository is a key that leaks.
    """
    _name = 'leih.sms.config'
    _description = 'SMS Gateway Settings'

    name = fields.Char(default='SMS Gateway', required=True)
    company_id = fields.Many2one(
        'res.company', default=lambda s: s.env.company, required=True)
    active = fields.Boolean('Sending Enabled', default=True)
    test_mode = fields.Boolean(
        'Test Mode (do not actually send)',
        help='Everything runs as normal and is logged, but nothing is handed '
             'to the gateway. Use it to check the message text and the numbers '
             'before real texts start going out.')

    endpoint_url = fields.Char('Endpoint', default=DEFAULT_ENDPOINT, required=True)
    sender_id = fields.Char('Sender ID')
    api_key = fields.Char('API Key')
    client_id = fields.Char('Client ID')
    country_code = fields.Char(
        'Country Code', default='880',
        help='Prefixed to local numbers. 880 for Bangladesh. No plus sign.')
    timeout = fields.Integer(
        'Timeout (seconds)', default=10,
        help='A counter must not sit waiting on a slow gateway.')

    send_on_appointment_confirm = fields.Boolean(
        'Text the patient when a serial is confirmed', default=True)
    appointment_template = fields.Text(
        'Appointment Message',
        default=("Dear {patient}, your appointment with {doctor} is confirmed "
                 "for {day} {date} at {time}. Serial: {serial}. {hospital}"),
        help='Placeholders: {patient} {doctor} {date} {day} {time} {session} '
             '{serial} {token} {fee} {hn} {hospital} {location}. An unknown '
             'placeholder is left blank rather than breaking the message.\n'
             'Keep it under 160 characters or the gateway bills it as two.')

    @api.model
    def _get(self):
        # sudo: the desk confirming a serial needs no rights over gateway
        # credentials, but the send has to be able to read them.
        cfg = self.sudo().search([('company_id', '=', self.env.company.id)], limit=1)
        if not cfg:
            cfg = self.sudo().create({'company_id': self.env.company.id})
        return cfg

    def action_open_settings(self):
        """Open the one settings record, creating it if it is not there yet.

        A plain act_window on a form view with no res_id opens a *blank* form,
        which looks like the settings have vanished and quietly invites a second
        configuration record that nothing reads.
        """
        cfg = self._get()
        return {
            'type': 'ir.actions.act_window',
            'name': _('SMS Gateway'),
            'res_model': 'leih.sms.config',
            'res_id': cfg.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _ready(self):
        self.ensure_one()
        return bool(self.active and self.endpoint_url and self.api_key
                    and self.client_id and self.sender_id)

    # ------------------------------------------------------------------
    def _normalise_number(self, number):
        """Local number -> the international form the gateway expects.

        01712345678, +880 1712-345678 and 8801712345678 are the same phone
        written three ways, and all three turn up in patient records.
        """
        self.ensure_one()
        digits = re.sub(r'\D', '', number or '')
        if not digits:
            return ''
        code = re.sub(r'\D', '', self.country_code or '880')
        if digits.startswith('00'):
            digits = digits[2:]
        if code and digits.startswith(code):
            return digits
        return code + digits.lstrip('0')

    def _payload(self, number, message):
        self.ensure_one()
        return {
            'senderId': self.sender_id or '',
            'is_Unicode': False,
            'is_Flash': False,
            'dataCoding': 0,
            'schedTime': '',
            'groupId': '',
            'message': message,
            'mobileNumbers': number,
            'serviceId': '',
            'coRelator': '',
            'linkId': '',
            'principleEntityId': '',
            'templateId': '',
            'apiKey': self.api_key or '',
            'clientId': self.client_id or '',
        }

    def send_sms(self, number, message, source=None):
        """Send one message and log it. Never raises.

        Returns the ``leih.sms.message`` record. Callers are counter actions --
        confirming a serial, registering an arrival -- and none of them should
        fail because a gateway is unreachable, so every error path ends in a
        logged failure rather than an exception.
        """
        self.ensure_one()
        Message = self.env['leih.sms.message'].sudo()
        to = self._normalise_number(number)
        log = Message.create({
            'number_raw': number or '',
            'number': to,
            'body': message or '',
            'source_model': source and source._name or False,
            'source_res_id': source and source.id or False,
            'state': 'draft',
        })
        if not to:
            return log._fail(_('No mobile number on the record.'))
        if not message:
            return log._fail(_('The message came out empty; check the template.'))
        if not self._ready():
            return log._fail(_('The SMS gateway is not configured or is switched off.'))
        if self.test_mode:
            log.write({'state': 'test', 'response': 'Test mode - not sent.'})
            return log
        try:
            reply = requests.post(
                self.endpoint_url, json=self._payload(to, message),
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout or 10)
        except requests.RequestException as err:
            return log._fail(_('Could not reach the gateway: %s', err))
        body = (reply.text or '')[:2000]
        if reply.status_code >= 400:
            return log._fail(_('Gateway returned HTTP %(code)s: %(body)s',
                               code=reply.status_code, body=body))
        # This gateway answers HTTP 200 even when it rejects a message and
        # reports the real outcome in the body, so trusting the status code
        # alone would file every rejection as "sent" and nobody would know the
        # patient was never told.
        failure = self._reply_failure(body)
        if failure:
            log.write({'response': body})
            return log._fail(failure)
        log.write({'state': 'sent', 'response': body,
                   'sent_on': fields.Datetime.now()})
        _logger.info('SMS sent to %s (%s)', to, log.source_model or 'manual')
        return log

    @staticmethod
    def _reply_failure(body):
        """The gateway's own error, or '' when it accepted the message.

        Shape seen in practice:
        {"ErrorCode":0,"ErrorDescription":null,
         "Data":[{"MessageErrorCode":0,"MessageErrorDescription":"Success",...}]}
        Anything non-zero at either level is a rejection. A body that cannot be
        parsed is *not* treated as a failure -- the message may well have gone,
        and inventing a failure would be as misleading as missing one.
        """
        try:
            data = json.loads(body or '{}')
        except (ValueError, TypeError):
            return ''
        if not isinstance(data, dict):
            return ''
        if data.get('ErrorCode'):
            return _('Gateway error %(code)s: %(desc)s',
                     code=data['ErrorCode'],
                     desc=data.get('ErrorDescription') or _('no description'))
        for item in data.get('Data') or []:
            if isinstance(item, dict) and item.get('MessageErrorCode'):
                return _('Gateway rejected %(number)s: %(desc)s',
                         number=item.get('MobileNumber') or '?',
                         desc=item.get('MessageErrorDescription') or _('no reason given'))
        return ''

    def action_send_test(self):
        """Send one message to the test number, to prove the setup works."""
        self.ensure_one()
        if not self.test_number:
            raise UserError(_('Enter a number to send the test to.'))
        log = self.send_sms(self.test_number,
                            self.test_message or 'LEIS test message.')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Test message'),
                'message': (_('Sent. Gateway said: %s', log.response or '(nothing)')
                            if log.state in ('sent', 'test')
                            else _('Failed: %s', log.error)),
                'type': 'success' if log.state in ('sent', 'test') else 'danger',
                'sticky': True,
            },
        }

    test_number = fields.Char('Test To')
    test_message = fields.Char('Test Message', default='LEIS test message.')
