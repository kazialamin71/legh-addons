"""The payment ``type`` fields are gone; ``payment_type`` is the only one left.

Three different things were all called ``type``:

* ``leih.money.receipt.type`` -- already a ``payment.type`` many2one, just
  misnamed. The column is renamed so the ids survive.
* the payment lines (bill / admission / general admission / optics) stored the
  payment type *name* as text. Those are resolved back to ``payment.type`` ids
  and the text column is dropped.
* ``bill.register`` / ``hospital.admission`` / ``leih.admission`` /
  ``optics.sale`` carried a legacy ``cash``/``bank`` selection next to the real
  ``payment_type``. ``cash`` rows that never got a ``payment_type`` are pointed
  at the Cash type; the column then goes.

Every step is guarded so re-running the script on an already-converted database
is a no-op.
"""
import logging

_logger = logging.getLogger(__name__)

# table -> the model each payment line belongs to (for logging only)
LINE_TABLES = (
    'bill_register_payment_line',
    'admission_payment_line',
    'general_admission_payment_line',
    'optics_sale_payment_line',
)

# Documents that carried the legacy cash/bank selection.
SELECTION_TABLES = (
    'bill_register',
    'hospital_admission',
    'leih_admission',
    'optics_sale',
)


def _has_column(cr, table, column):
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = %s AND column_name = %s
    """, (table, column))
    return bool(cr.fetchone())


def _has_table(cr, table):
    cr.execute("SELECT to_regclass(%s)", (table,))
    return cr.fetchone()[0] is not None


def _rename_money_receipt_column(cr):
    if not _has_table(cr, 'leih_money_receipt'):
        return
    if not _has_column(cr, 'leih_money_receipt', 'type'):
        return
    if _has_column(cr, 'leih_money_receipt', 'payment_type'):
        # Both present: the new column was created by an earlier partial run.
        cr.execute("""
            UPDATE leih_money_receipt
               SET payment_type = "type"
             WHERE payment_type IS NULL AND "type" IS NOT NULL
        """)
        cr.execute('ALTER TABLE leih_money_receipt DROP COLUMN "type"')
    else:
        cr.execute('ALTER TABLE leih_money_receipt RENAME COLUMN "type" TO payment_type')
    _logger.info('leih.money.receipt: type -> payment_type')


def _convert_line_table(cr, table):
    if not _has_table(cr, table) or not _has_column(cr, table, 'type'):
        return
    if not _has_column(cr, table, 'payment_type'):
        # Plain integer: _auto_init recognises it and only adds the foreign key.
        cr.execute('ALTER TABLE %s ADD COLUMN payment_type integer' % table)

    # The text held the payment type name ("Cash", "Visa Card", ...).
    cr.execute("""
        UPDATE {table} l
           SET payment_type = pt.id
          FROM payment_type pt
         WHERE l.payment_type IS NULL
           AND l."type" IS NOT NULL
           AND lower(btrim(l."type")) = lower(btrim(pt.name))
    """.format(table=table))
    matched = cr.rowcount

    cr.execute("""
        SELECT DISTINCT btrim("type") FROM {table}
         WHERE payment_type IS NULL AND btrim(COALESCE("type", '')) <> ''
    """.format(table=table))
    unmatched = [row[0] for row in cr.fetchall()]

    cr.execute('ALTER TABLE %s DROP COLUMN "type"' % table)
    _logger.info('%s: resolved %s payment type name(s) to payment_type', table, matched)
    if unmatched:
        # Left NULL rather than guessed at; the receipt still carries the type.
        _logger.warning(
            '%s: %s payment type name(s) matched no payment.type record and were '
            'cleared: %s', table, len(unmatched), ', '.join(sorted(unmatched)[:20]))


def _drop_selection_column(cr, table):
    if not _has_table(cr, table) or not _has_column(cr, table, 'type'):
        return
    if _has_column(cr, table, 'payment_type'):
        cr.execute("""
            UPDATE {table} d
               SET payment_type = pt.id
              FROM payment_type pt
             WHERE d.payment_type IS NULL
               AND lower(btrim(COALESCE(d."type", ''))) = 'cash'
               AND lower(btrim(pt.name)) = 'cash'
        """.format(table=table))
        if cr.rowcount:
            _logger.info('%s: %s cash row(s) given the Cash payment type',
                         table, cr.rowcount)
        cr.execute("""
            SELECT COUNT(*) FROM {table}
             WHERE payment_type IS NULL AND btrim(COALESCE("type", '')) <> ''
        """.format(table=table))
        orphans = cr.fetchone()[0]
        if orphans:
            # "bank" says nothing about which bank type was used, so these are
            # left for the desk rather than pointed at an arbitrary record.
            _logger.warning(
                '%s: %s row(s) had a legacy payment type but no payment_type; '
                'set one from the form if the mode matters.', table, orphans)
    cr.execute('ALTER TABLE %s DROP COLUMN "type"' % table)
    _logger.info('%s: dropped legacy cash/bank type column', table)


def migrate(cr, version):
    if not version:
        return
    _rename_money_receipt_column(cr)
    for table in LINE_TABLES:
        _convert_line_table(cr, table)
    for table in SELECTION_TABLES:
        _drop_selection_column(cr, table)
