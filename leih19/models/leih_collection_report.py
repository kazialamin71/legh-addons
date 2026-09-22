from odoo import fields, models, tools

# Where the money was taken. Kept as a plain selection (not a m2o) so a new
# counter only needs a new branch in the SQL, not master data.
COLLECTION_SECTIONS = [
    ('bill', 'Bill / Diagnostic'),
    ('admission', 'Admission'),
    ('opd', 'OPD'),
    ('pharmacy', 'Pharmacy'),
    ('optics', 'Optics'),
    ('other', 'Other'),
]


class LeihCollectionReport(models.Model):
    """Every rupee received, whoever received it, wherever it was received.

    A read-only SQL view unioning each collection point in the system, so one
    screen answers "who collected how much, at which counter, between these two
    timestamps". Modules that add a counter of their own extend
    ``_select_queries`` instead of touching this SQL (see leih_opd for the
    pharmacy / POS branch).

    Deliberately built on the *receipt* of each source rather than the paid
    amount on the document: bill and admission payments both write a
    ``leih.money.receipt``, so reading the documents as well would double count.
    """
    _name = 'leih.collection.report'
    _description = 'User-wise Cash Collection'
    _auto = False
    _order = 'collected_on desc'
    _rec_name = 'reference'

    collected_on = fields.Datetime('Collected On', readonly=True)
    date = fields.Date('Date', readonly=True)
    user_id = fields.Many2one('res.users', string='Collected By', readonly=True)
    section = fields.Selection(COLLECTION_SECTIONS, string='Section', readonly=True)
    payment_method = fields.Char('Payment Method', readonly=True)
    patient_name = fields.Many2one('patient.info', string='Patient', readonly=True)
    reference = fields.Char('Reference', readonly=True)
    amount = fields.Float('Amount', readonly=True)
    source_model = fields.Char('Source Document', readonly=True)
    source_res_id = fields.Integer('Source Id', readonly=True)

    # ------------------------------------------------------------------
    # SQL
    # ------------------------------------------------------------------
    def _has_column(self, table, column):
        self.env.cr.execute("""
            SELECT 1 FROM information_schema.columns
             WHERE table_name = %s AND column_name = %s
        """, (table, column))
        return bool(self.env.cr.fetchone())

    def _select_queries(self):
        """SELECTs unioned into the view. Override to add a counter."""
        return [self._select_money_receipts(), self._select_opd_tickets()]

    def _has_legacy_opd_receipts(self):
        """OPD tickets briefly raised a ``leih.money.receipt`` of their own.

        They no longer do -- the ticket *is* the OPD money document -- but the
        receipts raised while they did are still in the table, and they have to
        be kept out of the receipt branch or the ticket branch would report the
        same money a second time.
        """
        return self._has_column('leih_money_receipt', 'opd_ticket_id')

    def _select_money_receipts(self):
        """Bill, admission and optics money -- all of it lands in a receipt."""
        return """
            SELECT r.id AS source_res_id,
                   'leih.money.receipt'::varchar AS source_model,
                   r.create_date AS collected_on,
                   COALESCE(r.date, r.create_date::date) AS date,
                   COALESCE(r.user_id, r.create_uid) AS user_id,
                   CASE WHEN r.bill_id IS NOT NULL THEN 'bill'
                        WHEN r.general_admission_id IS NOT NULL
                              OR r.admission_id IS NOT NULL THEN 'admission'
                        WHEN r.optics_sale_id IS NOT NULL THEN 'optics'
                        ELSE 'other' END::varchar AS section,
                   pt.name AS payment_method,
                   COALESCE(b.patient_name, ha.patient_name,
                            la.patient_name, os.patient_name) AS patient_name,
                   r.name AS reference,
                   r.amount AS amount
              FROM leih_money_receipt r
         LEFT JOIN payment_type pt ON pt.id = r.payment_type
         LEFT JOIN bill_register b ON b.id = r.bill_id
         LEFT JOIN hospital_admission ha ON ha.id = r.general_admission_id
         LEFT JOIN leih_admission la ON la.id = r.admission_id
         LEFT JOIN optics_sale os ON os.id = r.optics_sale_id
             WHERE r.state = 'confirm'
               AND COALESCE(r.amount, 0) <> 0
               %(opd_exclude)s
        """ % {'opd_exclude': ('AND r.opd_ticket_id IS NULL'
                               if self._has_legacy_opd_receipts() else '')}

    def _select_opd_tickets(self):
        """OPD money is read off the ticket, which is the OPD money document.

        It raises no receipt of its own: a confirmed ticket posts its journal
        entry and goes straight onto the OPD collection sheet.
        """
        return """
            SELECT t.id AS source_res_id,
                   'opd.ticket'::varchar AS source_model,
                   t.create_date AS collected_on,
                   COALESCE(t.date, t.create_date::date) AS date,
                   COALESCE(t.user_id, t.create_uid) AS user_id,
                   'opd'::varchar AS section,
                   %(payment_method)s AS payment_method,
                   t.patient_name AS patient_name,
                   t.name AS reference,
                   t.total AS amount
              FROM opd_ticket t
                   %(payment_join)s
             WHERE t.already_collected = TRUE
               AND COALESCE(t.state, 'confirmed') <> 'cancelled'
               AND COALESCE(t.total, 0) <> 0
        """ % ({
            'payment_method': 'tpt.name',
            'payment_join': 'LEFT JOIN payment_type tpt ON tpt.id = t.payment_type',
        } if self._has_column('opd_ticket', 'payment_type') else {
            'payment_method': 'NULL::varchar',
            'payment_join': '',
        })

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        union = ' UNION ALL '.join(self._select_queries())
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT ROW_NUMBER() OVER (ORDER BY x.collected_on DESC) AS id, x.*
                  FROM (%s) x
            )
        """ % (self._table, union))

    # ------------------------------------------------------------------
    # Drill-down
    # ------------------------------------------------------------------
    def action_open_source(self):
        """Open the receipt / ticket a report line came from."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.source_model,
            'res_id': self.source_res_id,
            'view_mode': 'form',
            'target': 'current',
        }
