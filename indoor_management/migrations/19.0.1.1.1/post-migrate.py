"""Recompute only the bed lines that are currently billing nothing.

Charge thresholds moved out of module constants (6h half day, 12h full day)
into ``bed.charge.rule``, seeded with the hospital's own bands (2h / 6h). A
stored compute is not revisited just because the rule behind it changed, which
is deliberate here: a released admission has already been settled and printed,
and restating its accommodation charge months later would contradict a receipt
the patient is holding. Past stays keep what they were billed; the new bands
apply to stays still running and to anything edited from now on.

The exception is a line billing zero on a patient who is still in the bed.
Those come from an old create-order bug -- ``manual_override`` being set before
``start_date`` reached the cache made the first compute see no start date, and
the line stayed at zero days for the whole stay. That is not a historical
price, it is an ongoing under-bill, so those lines are asked to compute again.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    Line = env['hospital.bed.line']
    stale = Line.search([
        ('days_count', '=', 0),
        ('start_date', '!=', False),
        ('bed_no', '!=', False),
        ('manual_override', '=', False),
        ('hospital_bed_item_id.state', '=', 'activated'),
    ])
    if not stale:
        return
    names = stale.mapped('hospital_bed_item_id.name')
    stale._compute_charges()
    env.flush_all()
    _logger.warning(
        'indoor: recomputed %s accommodation line(s) that were billing zero '
        'days on a patient still admitted (%s). Check the bed charge on those '
        'admissions before settling them.', len(stale), ', '.join(names))
