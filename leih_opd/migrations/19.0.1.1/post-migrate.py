"""Backfill ``appointment.booking.date`` from ``appointment_date``.

``date`` is the base module's only date field and leih19's booking report still
prints it, but nothing in the OPD flow ever sets it -- the whole flow works off
``appointment_date``. It is now a stored compute seeded from ``appointment_date``,
which fixes every booking taken from here on.

It does not fix the ones already in the table: ``date`` is an existing column, so
Odoo does not queue a recompute for rows that predate the compute. Hence this.

Only rows whose ``date`` is still NULL are touched, so a desk that did fill the
field in by hand keeps what it typed, and re-running the script is a no-op.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute('UPDATE appointment_booking SET date = appointment_date'
               ' WHERE date IS NULL AND appointment_date IS NOT NULL')
    if cr.rowcount:
        _logger.info('appointment.booking: seeded date on %s booking(s) from '
                     'appointment_date', cr.rowcount)
