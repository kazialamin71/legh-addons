def migrate(cr, version):
    """``opd.ticket.line.total_amount`` and ``opd.ticket.total`` became stored
    computed fields. Odoo does not recompute an existing column, so backfill the
    tickets that were saved while nothing filled those amounts in."""
    cr.execute("""
        UPDATE opd_ticket_line
           SET total_amount = price
         WHERE COALESCE(total_amount, 0) = 0
           AND COALESCE(price, 0) <> 0
    """)
    cr.execute("""
        UPDATE opd_ticket t
           SET total = s.amount
          FROM (SELECT opd_ticket_id, SUM(total_amount) AS amount
                  FROM opd_ticket_line
                 WHERE opd_ticket_id IS NOT NULL
              GROUP BY opd_ticket_id) s
         WHERE s.opd_ticket_id = t.id
           AND COALESCE(t.total, 0) = 0
    """)
    migrate_visit_lines(cr)


def migrate_visit_lines(cr):
    """``doctor.profile.admission.line`` gained a visit date/time and its total
    became a stored computed field. Seed both for rows created before that."""
    cr.execute("""
        UPDATE doctor_profile_admission_line
           SET visit_datetime = create_date
         WHERE visit_datetime IS NULL
    """)
    cr.execute("""
        UPDATE doctor_profile_admission_line
           SET total_amount = COALESCE(visit_fee, 0) * GREATEST(COALESCE(doctor_visit_qty, 1), 1)
         WHERE COALESCE(total_amount, 0) = 0
           AND COALESCE(visit_fee, 0) <> 0
    """)
