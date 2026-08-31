"""Retype ``appointment.booking.sex`` and ``.time``.

Both fields used to be free-text ``Char``. ``sex`` becomes a selection and
``time`` becomes a float behind the ``float_time`` widget.

``sex`` keeps its varchar column, so only the values need normalising -- but
``time`` changes column type, and Odoo's own conversion is a bare
``ALTER COLUMN ... USING "time"::double precision``. That blows up on the first
row holding "10:30 AM", taking the whole upgrade with it. So the column is
converted here, before ``_auto_init`` gets to it, with the text parsed in
Python where the ragged old formats can actually be read.

Every step is guarded, because Odoo re-runs major-less migration scripts on
later upgrades: on a database that has already been converted this is a no-op.
"""
import logging
import re

_logger = logging.getLogger(__name__)

TABLE = 'appointment_booking'

# "10:30 AM", "10.30am", "1030", "10", "10:30:00", "০" -- whatever the desk typed.
_TIME_RE = re.compile(
    r'^\s*(\d{1,2})\s*(?:[:.\-]\s*(\d{1,2}))?\s*(?::\s*\d{1,2})?\s*([ap])?\.?\s*m?\.?\s*$',
    re.IGNORECASE)


def _parse_time(text):
    """Free-text clock time -> hours since midnight, or None if unreadable."""
    if not text:
        return None
    raw = text.strip()
    match = _TIME_RE.match(raw)
    if match:
        hours, minutes, meridiem = match.group(1), match.group(2), match.group(3)
        hours, minutes = int(hours), int(minutes or 0)
    elif re.fullmatch(r'\s*\d{3,4}\s*', raw):
        # Bare "930" / "1030", written the way a clock face reads.
        digits = raw.strip()
        hours, minutes, meridiem = int(digits[:-2]), int(digits[-2:]), None
    else:
        return None
    if minutes > 59:
        return None
    if meridiem:
        meridiem = meridiem.lower()
        if hours == 12:
            hours = 0
        if meridiem == 'p':
            hours += 12
    if hours > 23:
        return None
    return hours + minutes / 60.0


def _column_type(cr, column):
    cr.execute("""
        SELECT data_type FROM information_schema.columns
         WHERE table_name = %s AND column_name = %s
    """, (TABLE, column))
    row = cr.fetchone()
    return row[0] if row else None


def _migrate_time(cr):
    if _column_type(cr, 'time') != 'character varying':
        # Already converted, or the column does not exist yet (fresh install).
        return

    cr.execute('SELECT id, "time" FROM appointment_booking'
               ' WHERE "time" IS NOT NULL AND btrim("time") <> %s', ('',))
    parsed, unreadable = [], []
    for booking_id, text in cr.fetchall():
        value = _parse_time(text)
        if value is None:
            unreadable.append((booking_id, text))
        else:
            parsed.append((booking_id, value))

    # USING NULL rather than a cast: the old text is already read out above, and
    # a cast is exactly what would fail here.
    cr.execute('ALTER TABLE appointment_booking'
               ' ALTER COLUMN "time" DROP DEFAULT,'
               ' ALTER COLUMN "time" TYPE double precision USING NULL')
    for booking_id, value in parsed:
        cr.execute('UPDATE appointment_booking SET "time" = %s WHERE id = %s',
                   (value, booking_id))

    _logger.info('appointment.booking.time: converted %s value(s) to float time',
                 len(parsed))
    if unreadable:
        # Left at NULL rather than guessed at. Logged so the desk can retype the
        # handful that were never a clock time in the first place.
        _logger.warning(
            'appointment.booking.time: %s value(s) could not be read as a time '
            'and were cleared: %s', len(unreadable),
            ', '.join('id=%s %r' % pair for pair in unreadable[:20]))


def _migrate_sex(cr):
    if _column_type(cr, 'sex') != 'character varying':
        return
    cr.execute("""
        UPDATE appointment_booking
           SET sex = CASE
                   WHEN lower(btrim(sex)) IN ('m', 'male') THEN 'male'
                   WHEN lower(btrim(sex)) IN ('f', 'female') THEN 'female'
                   WHEN btrim(sex) = '' THEN NULL
                   ELSE 'others'
               END
         WHERE sex IS NOT NULL
           AND sex NOT IN ('male', 'female', 'others')
    """)
    if cr.rowcount:
        _logger.info('appointment.booking.sex: normalised %s free-text value(s)',
                     cr.rowcount)


def migrate(cr, version):
    if not version:
        return
    _migrate_sex(cr)
    _migrate_time(cr)
