def migrate(cr, version):
    """charge_type is a stored related on the (now repointed) item field; the
    ORM does not recompute an existing column, so seed it from the catalogue."""
    cr.execute("""
        UPDATE hospital_admission_line l
           SET charge_type = i.charge_type
          FROM admission_charge_item i
         WHERE i.id = l.name
           AND l.charge_type IS DISTINCT FROM i.charge_type
    """)
