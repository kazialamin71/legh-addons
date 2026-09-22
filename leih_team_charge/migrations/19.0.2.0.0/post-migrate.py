"""The doctor's share becomes a real payable, settled once instead of per receipt.

Two things to carry forward:

* ``team_settled`` was a flag set by stamping ``team_settlement_id``. It is now
  derived from ``team_paid``, so a share that was marked paid under the old
  scheme has to be given an amount or it would look unpaid and be handed over a
  second time. ``team_entitled`` follows it: money already out of the door was
  by definition earned.
* ``team_charge_treatment`` and ``team_allocation`` are gone. They chose between
  two wrong behaviours -- keeping the counter's own cash off the ledger, and
  guessing the split receipt by receipt before the charges were known.

Nothing is posted here. What the old scheme never put on the ledger stays off it
until someone asks for it; see the "Doctor's Share" report.
"""
import logging

_logger = logging.getLogger(__name__)

CARRIERS = ('hospital_admission_charge', 'bill_register_line')


def migrate(cr, version):
    if not version:
        return
    for table in CARRIERS:
        cr.execute("""
            SELECT 1 FROM information_schema.columns
             WHERE table_name = %s AND column_name = 'team_paid'
        """, (table,))
        if not cr.fetchone():
            continue
        cr.execute("""
            UPDATE {table}
               SET team_paid = COALESCE(team_amount, 0),
                   team_entitled = COALESCE(team_amount, 0)
             WHERE team_settlement_id IS NOT NULL
               AND COALESCE(team_paid, 0) = 0
               AND COALESCE(team_amount, 0) > 0
        """.format(table=table))
        _logger.info('%s: %s share(s) carried forward as already paid.',
                     table, cr.rowcount)
