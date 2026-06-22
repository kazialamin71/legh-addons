import logging

_logger = logging.getLogger(__name__)


def pre_init_hook(env):
    """Wipe legacy hospital.bed data and drop columns whose type will change.

    The user opted for a fresh install — old hospital.bed.ward_name (Char) and
    bed_qty (Char) become Many2one/Integer respectively, which Odoo cannot
    convert in place. We drop them so Odoo recreates with the new types.
    """
    cr = env.cr
    cr.execute("SELECT to_regclass('public.hospital_bed')")
    if cr.fetchone()[0]:
        _logger.info("indoor_management: truncating legacy hospital_bed data")
        cr.execute("TRUNCATE TABLE hospital_bed RESTART IDENTITY CASCADE")
        for col in ("ward_name", "bed_qty"):
            cr.execute(
                "ALTER TABLE hospital_bed DROP COLUMN IF EXISTS %s" % col
            )

    cr.execute("SELECT to_regclass('public.hospital_bed_line')")
    if cr.fetchone()[0]:
        _logger.info("indoor_management: clearing legacy hospital_bed_line rows")
        cr.execute("DELETE FROM hospital_bed_line")
        for col in ("ward_name", "bed_qty"):
            cr.execute(
                "ALTER TABLE hospital_bed_line DROP COLUMN IF EXISTS %s" % col
            )
