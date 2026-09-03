{
    'name': 'LEIS SMS',
    'summary': 'Send SMS through the hospital gateway, and keep a record of '
               'every message',
    'description': """
LEIS SMS
========

A thin, logged wrapper around the hospital's SMS gateway, plus the first thing
it is wanted for: a confirmation text to the patient when an appointment serial
is confirmed.

Two things it deliberately does:

* **Every message is a record.** SMS costs money and gateways fail quietly.
  ``leih.sms.message`` keeps the number, the text, the gateway's reply and the
  document it came from, so "did the patient get told?" is answerable.
* **A failure never blocks the counter.** If the gateway is down, the serial is
  still confirmed and the failure is logged. Nobody should be unable to book a
  patient because a text could not be sent.

Credentials live in the configuration record, not in the source.
""",
    'version': '19.0.1.0.2',
    'author': 'Kazi Alamin',
    'category': 'Tools',
    'depends': ['leih_opd'],
    'data': [
        'security/ir.model.access.csv',
        'views/leih_sms_config_views.xml',
        'views/leih_sms_message_views.xml',
        'views/menus.xml',
    ],
    'license': 'LGPL-3',
    'application': False,
}
