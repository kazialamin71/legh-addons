"""Backfill the ward catalogue link on charges that already exist.

``hospital.admission.charge`` now records ``charge_item_id`` so the doctor's
share configured on ``admission.charge.item`` can be read. Charges created
before this only carry ``source_model`` / ``source_res_id``, which is enough to
find the line and therefore the item.

Done here so existing admissions pick the share up on their own, rather than
each one having to be recalculated by hand.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        UPDATE hospital_admission_charge c
           SET charge_item_id = l.name
          FROM hospital_admission_line l
         WHERE c.source_model = 'hospital.admission.line'
           AND c.source_res_id = l.id
           AND l.name IS NOT NULL
           AND c.charge_item_id IS NULL
    """)
    linked = cr.rowcount
    if not linked:
        _logger.info('team charge: no ward charges needed a catalogue link')
        return
    _logger.info('team charge: linked %s ward charge(s) to their catalogue item',
                 linked)

    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    model = env.get('hospital.admission.charge')
    charges = model.search([('charge_item_id', '!=', False)])
    for fname in ('team_share_method', 'team_share_value',
                  'team_amount', 'hospital_amount'):
        field = model._fields.get(fname)
        if field:
            env.add_to_compute(field, charges)
    env.flush_all()

    admissions = charges.mapped('admission_id')
    Adm = env['hospital.admission']
    for fname in ('team_charge_total', 'hospital_charge_total'):
        field = Adm._fields.get(fname)
        if field:
            env.add_to_compute(field, admissions)
    env.flush_all()
    _logger.info('team charge: recomputed the split on %s admission(s)',
                 len(admissions))
