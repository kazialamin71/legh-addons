"""'Paid Now' is collected when the bill is confirmed, not when it is saved.

Until now ``bill.register.create`` receipted ``down_payment`` immediately, and
nothing ever looked at the field again - so a bill saved with 0 and then edited
to 100 kept the 100 on the form while ``paid`` and ``due`` stayed untouched, and
no money receipt or journal entry was ever raised for it.

``down_payment_registered`` now records how much of "Paid Now" has become a
receipt. Existing rows need it seeded, or ``due`` would subtract the same money
twice: once as a payment line and once as a still-pending counter collection.

The seed is ``LEAST(down_payment, paid)``, which repairs both populations in one
pass: a bill whose down payment was receipted at create has ``paid`` at least as
large, so it is marked fully converted; a bill left broken by the old behaviour
has ``paid`` of 0, so its "Paid Now" stays pending and is collected the next time
the bill is confirmed - which is what should have happened all along.

Guarded, because Odoo re-runs major-less migration scripts on later upgrades.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        UPDATE bill_register
           SET down_payment_registered = LEAST(COALESCE(down_payment, 0.0),
                                               COALESCE(paid, 0.0))
         WHERE COALESCE(down_payment, 0.0) > 0.0
           AND COALESCE(down_payment_registered, 0.0) = 0.0
        RETURNING id
    """)
    ids = [row[0] for row in cr.fetchall()]
    if not ids:
        return

    # ``due`` is stored, so the rows whose pending amount just changed have to
    # be recomputed through the ORM rather than patched in SQL.
    env = api.Environment(cr, SUPERUSER_ID, {})
    bills = env['bill.register'].browse(ids)
    bills.modified(['down_payment_registered'])
    env.flush_all()
    _logger.info("bill.register: seeded down_payment_registered on %s bills", len(ids))
