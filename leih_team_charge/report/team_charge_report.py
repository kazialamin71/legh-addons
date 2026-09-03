from odoo import fields, models, tools


class TeamChargeReport(models.Model):
    """One line per charge, from both counters, with the money split three ways.

    The reconciliation this exists to make possible:

        charged  =  hospital share  +  doctor share
        collected      =  hospital collected  +  doctor collected
        doctor payable =  doctor collected    -  doctor settled

    Under the off-ledger treatment the general ledger only ever saw the hospital
    column, so this view is the *only* record of the rest. It reads the charge
    lines directly rather than any cached total, so it cannot drift away from
    what was actually billed.
    """
    _name = 'team.charge.report'
    _description = 'Doctor Share Reconciliation'
    _auto = False
    _order = 'date desc, id desc'
    _rec_name = 'reference'

    date = fields.Date('Date', readonly=True)
    source = fields.Selection(
        [('admission', 'Admission'), ('bill', 'Bill / Diagnostic')],
        string='Source', readonly=True)
    reference = fields.Char('Document', readonly=True)
    patient_id = fields.Many2one('patient.info', string='Patient', readonly=True)
    doctor_id = fields.Many2one('doctors.profile', string='Doctor', readonly=True)
    item = fields.Char('Item', readonly=True)

    charged = fields.Float('Charged', readonly=True)
    hospital_amount = fields.Float('Hospital Share', readonly=True)
    team_amount = fields.Float("Doctor's Share", readonly=True)

    paid_ratio = fields.Float('Collected %', readonly=True, group_operator='avg')
    collected = fields.Float('Collected', readonly=True)
    hospital_collected = fields.Float('Hospital Collected', readonly=True)
    team_collected = fields.Float("Doctor's Collected", readonly=True)

    team_settled = fields.Float('Paid to Doctor', readonly=True)
    team_payable = fields.Float('Still Owed to Doctor', readonly=True)

    settlement_id = fields.Many2one(
        'team.charge.settlement', string='Settlement', readonly=True)
    is_settled = fields.Boolean('Settled', readonly=True)

    # ------------------------------------------------------------------
    def _select_admission(self):
        return """
            SELECT
                (c.id * 2)                              AS id,
                c.date::date                            AS date,
                'admission'                             AS source,
                a.name                                  AS reference,
                a.patient_name                          AS patient_id,
                c.team_provider_id                      AS doctor_id,
                COALESCE(e.name, c.description)         AS item,
                c.total_amount                          AS charged,
                c.hospital_amount                       AS hospital_amount,
                c.team_amount                           AS team_amount,
                r.ratio                                 AS paid_ratio,
                c.total_amount    * r.ratio             AS collected,
                c.hospital_amount * r.ratio             AS hospital_collected,
                c.team_amount     * r.ratio             AS team_collected,
                CASE WHEN c.team_settlement_id IS NULL THEN 0.0
                     ELSE c.team_amount END             AS team_settled,
                CASE WHEN c.team_settlement_id IS NULL
                     THEN c.team_amount * r.ratio
                     ELSE 0.0 END                       AS team_payable,
                c.team_settlement_id                    AS settlement_id,
                (c.team_settlement_id IS NOT NULL)      AS is_settled
              FROM hospital_admission_charge c
              JOIN hospital_admission a ON a.id = c.admission_id
              LEFT JOIN examination_entry e ON e.id = c.item_id
              JOIN LATERAL (
                    SELECT CASE WHEN COALESCE(a.grand_total, 0) <= 0 THEN 0.0
                                ELSE LEAST(GREATEST(
                                     COALESCE(a.paid, 0) / a.grand_total, 0), 1)
                           END AS ratio
              ) r ON TRUE
             WHERE c.team_provider_id IS NOT NULL
        """

    def _select_bill(self):
        return """
            SELECT
                (l.id * 2 + 1)                          AS id,
                b.date::date                            AS date,
                'bill'                                  AS source,
                b.name                                  AS reference,
                b.patient_name                          AS patient_id,
                l.team_provider_id                      AS doctor_id,
                e.name                                  AS item,
                l.total_amount                          AS charged,
                l.hospital_amount                       AS hospital_amount,
                l.team_amount                           AS team_amount,
                r.ratio                                 AS paid_ratio,
                l.total_amount    * r.ratio             AS collected,
                l.hospital_amount * r.ratio             AS hospital_collected,
                l.team_amount     * r.ratio             AS team_collected,
                CASE WHEN l.team_settlement_id IS NULL THEN 0.0
                     ELSE l.team_amount END             AS team_settled,
                CASE WHEN l.team_settlement_id IS NULL
                     THEN l.team_amount * r.ratio
                     ELSE 0.0 END                       AS team_payable,
                l.team_settlement_id                    AS settlement_id,
                (l.team_settlement_id IS NOT NULL)      AS is_settled
              FROM bill_register_line l
              JOIN bill_register b ON b.id = l.bill_register_id
              LEFT JOIN examination_entry e ON e.id = l.name
              JOIN LATERAL (
                    SELECT CASE WHEN COALESCE(b.grand_total, 0) <= 0 THEN 0.0
                                ELSE LEAST(GREATEST(
                                     COALESCE(b.paid, 0) / b.grand_total, 0), 1)
                           END AS ratio
              ) r ON TRUE
             WHERE l.team_provider_id IS NOT NULL
        """

    def init(self):
        # id is derived as (pk * 2) and (pk * 2 + 1) so the two sources cannot
        # collide -- a view needs a unique id and both tables start at 1.
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (%s UNION ALL %s)
        """ % (self._table, self._select_admission(), self._select_bill()))
