from . import models


def post_init_hook(env):
    """Backfill a res.partner for every existing patient on install."""
    env['patient.info']._backfill_partners()
