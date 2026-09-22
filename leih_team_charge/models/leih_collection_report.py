from odoo import fields, models


class LeihCollectionReport(models.Model):
    """The counter's cash goes out as well as in.

    A doctor takes their share from the counter, not from the accounts
    department, so a payout is a counter movement like any other -- it just has
    the opposite sign. Adding it here means the drawer at close is simply the
    sum of this screen: patient money in, doctors' money out.

    Without it the report only ever showed collections, and every day the
    counter appeared to hold more cash than it did.
    """
    _inherit = 'leih.collection.report'

    # A read-only SQL view, so nothing is ever deleted through the ORM and the
    # policy is academic -- but Odoo still insists on a valid one.
    section = fields.Selection(
        selection_add=[('team_payout', "Doctor's Share Paid Out")],
        ondelete={'team_payout': 'set null'})

    def _select_queries(self):
        return super()._select_queries() + [self._select_team_payouts()]

    def _select_team_payouts(self):
        """Doctor payouts, negative because the cash leaves the drawer."""
        return """
            SELECT s.id AS source_res_id,
                   'team.charge.settlement'::varchar AS source_model,
                   s.write_date AS collected_on,
                   s.date AS date,
                   COALESCE(s.write_uid, s.create_uid) AS user_id,
                   'team_payout'::varchar AS section,
                   pt.name AS payment_method,
                   NULL::integer AS patient_name,
                   s.name AS reference,
                   -s.amount AS amount
              FROM team_charge_settlement s
         LEFT JOIN payment_type pt ON pt.id = s.payment_type
             WHERE s.state = 'done'
               AND COALESCE(s.amount, 0) <> 0
        """
