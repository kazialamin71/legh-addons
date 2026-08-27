"""hospital.admission.line.name moved from examination.entry to the new
admission.charge.item catalogue.

The column keeps its name but now points at a different table, so the ids have
to be translated BEFORE the ORM rebuilds the foreign key -- otherwise the new
constraint fails against the old examination.entry ids.
"""


def migrate(cr, version):
    # Nothing to translate if the line table was never populated.
    cr.execute("SELECT COUNT(*) FROM hospital_admission_line WHERE name IS NOT NULL")
    if not cr.fetchone()[0]:
        _drop_old_fk(cr)
        return

    _drop_old_fk(cr)

    # One catalogue item per examination entry still referenced by a line.
    # Reuse an item of the same name when one already exists.
    cr.execute("""
        INSERT INTO admission_charge_item
                    (name, charge_type, rate, department, accounts_id, active,
                     create_uid, write_uid, create_date, write_date)
        SELECT e.name, 'other', e.rate, e.department, e.accounts_id, TRUE,
               1, 1, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC'
          FROM examination_entry e
         WHERE e.id IN (SELECT DISTINCT name FROM hospital_admission_line WHERE name IS NOT NULL)
           AND NOT EXISTS (SELECT 1 FROM admission_charge_item i
                            WHERE lower(btrim(i.name)) = lower(btrim(e.name)))
    """)

    # Translate every line to the matching catalogue item.
    cr.execute("""
        UPDATE hospital_admission_line l
           SET name = i.id
          FROM examination_entry e
          JOIN admission_charge_item i
            ON lower(btrim(i.name)) = lower(btrim(e.name))
         WHERE l.name = e.id
    """)

    # Anything left unmatched would break the new FK; clear it rather than fail.
    cr.execute("""
        UPDATE hospital_admission_line
           SET name = NULL
         WHERE name IS NOT NULL
           AND name NOT IN (SELECT id FROM admission_charge_item)
    """)


def _drop_old_fk(cr):
    cr.execute("""
        SELECT conname FROM pg_constraint
         WHERE conrelid = 'hospital_admission_line'::regclass
           AND contype = 'f'
           AND confrelid = 'examination_entry'::regclass
    """)
    for (conname,) in cr.fetchall():
        cr.execute(f'ALTER TABLE hospital_admission_line DROP CONSTRAINT "{conname}"')
