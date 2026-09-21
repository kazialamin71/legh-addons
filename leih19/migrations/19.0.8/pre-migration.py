"""Rename hospital.admission.reffered_to_hospital to referral.

``bill.register`` has called this exact field -- same model, same meaning --
``referral`` all along. The admission spelled it differently, and the cost of
that was not cosmetic: the field never made it onto the admission form, so the
referring broker could not be recorded on an admission at all, and every
commission rule that keys off a broker was dead on the ward side.

Renamed in pre-migration so the column survives with its data. Doing it in the
ORM instead would drop the old column and create an empty new one, losing the
referrer on every admission already recorded.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'hospital_admission'
           AND column_name = 'reffered_to_hospital'
    """)
    if not cr.fetchone():
        return
    cr.execute("""
        ALTER TABLE hospital_admission
        RENAME COLUMN reffered_to_hospital TO referral
    """)
    # ir.model.fields carries the old name too; leaving it behind makes the ORM
    # believe both fields exist and it will try to recreate the one just renamed.
    cr.execute("""
        DELETE FROM ir_model_fields
         WHERE model = 'hospital.admission'
           AND name = 'reffered_to_hospital'
    """)
    _logger.info('leih19: hospital.admission.reffered_to_hospital renamed to referral')
