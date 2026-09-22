"""``opd.ticket.name`` is now the ticket number, drawn from a sequence.

It used to be a free text field with nothing behind it, so existing tickets
carry whatever the counter happened to type -- usually the patient's name, often
nothing at all. Give every one of them a real OPD-xxxxx number so the ticket, its
money receipt, its journal entry and the cash collection report all refer to the
same document.

Rows that already look like a sequence number are left alone, so re-running this
never renumbers a ticket that has been printed.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        SELECT id FROM opd_ticket
         WHERE COALESCE(name, '') NOT LIKE 'OPD-%'
      ORDER BY COALESCE(date, create_date::date), id
    """)
    ids = [row[0] for row in cr.fetchall()]
    if not ids:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    sequence = env['ir.sequence']
    for ticket in env['opd.ticket'].browse(ids):
        # Oldest first, so the numbers run in the order the tickets were issued.
        ticket.name = sequence.next_by_code('opd.ticket') or ticket.name
    env.flush_all()
    _logger.info("opd.ticket: numbered %s ticket(s) from the OPD sequence", len(ids))
