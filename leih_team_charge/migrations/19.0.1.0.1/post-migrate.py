"""Recompute the hospital/doctor split on every existing charge.

``hospital_amount`` used to share its compute method with ``team_amount``.
Because ``team_amount`` is editable, the web client writes it on every save,
which makes Odoo consider that compute satisfied and skip it -- so
``hospital_amount`` was never written and stayed NULL. A NULL hospital share
reads as zero, so ``_acc_post_revenue`` found nothing to recognise, marked the
bill posted and produced no journal entry at all.

The two fields now have separate computes. Changing a compute method does not
make Odoo revisit rows that already exist, so they have to be asked for
explicitly here.
"""
import logging

_logger = logging.getLogger(__name__)

CARRIERS = ('bill.register.line', 'hospital.admission.charge')
# The document totals are stored too, and roll up from the lines, so they are
# just as stale as the lines were.
DOCUMENTS = ('bill.register', 'hospital.admission')


def migrate(cr, version):
    if not version:
        return
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    for model_name in CARRIERS:
        model = env.get(model_name)
        if model is None:
            continue
        records = model.search([])
        if not records:
            continue
        for fname in ('team_amount', 'hospital_amount'):
            field = model._fields.get(fname)
            if field:
                env.add_to_compute(field, records)
        env.flush_all()
        _logger.info('team charge: recomputed the split on %s %s record(s)',
                     len(records), model_name)

    for model_name in DOCUMENTS:
        model = env.get(model_name)
        if model is None:
            continue
        records = model.search([])
        if not records:
            continue
        for fname in ('team_charge_total', 'hospital_charge_total'):
            field = model._fields.get(fname)
            if field:
                env.add_to_compute(field, records)
        env.flush_all()
        _logger.info('team charge: recomputed totals on %s %s record(s)',
                     len(records), model_name)

    # A bill marked posted but carrying no journal entry never actually posted.
    # Clear the flag so confirming or reposting can do the work properly.
    cr.execute("""
        UPDATE bill_register b
           SET acc_revenue_posted = FALSE
         WHERE b.acc_revenue_posted
           AND NOT EXISTS (SELECT 1 FROM bill_register_acc_move_rel r
                            WHERE r.bill_id = b.id)
    """)
    if cr.rowcount:
        _logger.warning(
            'team charge: %s bill(s) were flagged as posted with no journal '
            'entry behind them; the flag has been cleared so they can post.',
            cr.rowcount)
