"""Turn each settlement's typed paid_amount into a payment record.

``commission.paid_amount`` was a plain Float that ``action_mark_paid`` wrote the
whole total into. It is computed from ``commission.payment`` rows now, so
without this every settlement already paid would recompute to zero paid and
show its full value outstanding again -- money that has gone out reappearing as
a debt.

The payment is dated from the settlement's own period end, which is the closest
thing the old data has to a payment date. It is marked confirmed, because the
figure it came from only ever meant "this has been paid".
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    cr.execute("""
        SELECT id, name, paid_amount, cal_end_date
          FROM commission
         WHERE COALESCE(paid_amount, 0) > 0
    """)
    rows = cr.fetchall()
    if not rows:
        return

    Payment = env['commission.payment']
    created = 0
    for settlement_id, name, paid_amount, cal_end_date in rows:
        if Payment.search_count([('cc_id', '=', settlement_id)]):
            continue
        payment = Payment.create({
            'cc_id': settlement_id,
            'paid_amount': paid_amount,
            'date': (cal_end_date.date() if cal_end_date else None),
            'note': 'Carried over from the settlement\'s Paid Amount when '
                    'commission payments became records.',
        })
        payment.state = 'done'
        created += 1

    env.flush_all()
    # The computed fields have to be filled from the payments just made.
    settlements = env['commission'].browse([r[0] for r in rows])
    for fname in ('net_payable_amount', 'paid_amount', 'balance_amount'):
        field = env['commission']._fields.get(fname)
        if field:
            env.add_to_compute(field, settlements)
    env.flush_all()
    for rec in settlements:
        rec._update_payment_state()
    env.flush_all()
    _logger.warning(
        'commission: created %s carry-over payment record(s) from the old '
        'typed Paid Amount. Check their dates -- they default to the '
        'settlement period end.', created)
