from odoo import models


class LeihCollectionReport(models.Model):
    """Add the pharmacy counter (POS) to the user-wise collection report.

    The POS branch lives here rather than in leih19 because point_of_sale is a
    dependency of this module only -- leih19 must still build its view on a
    database where POS is not installed.
    """
    _inherit = 'leih.collection.report'

    def _select_queries(self):
        return super()._select_queries() + [self._select_pos_payments()]

    def _select_pos_payments(self):
        return """
            SELECT p.id AS source_res_id,
                   'pos.payment'::varchar AS source_model,
                   p.payment_date AS collected_on,
                   p.payment_date::date AS date,
                   COALESCE(o.user_id, p.create_uid) AS user_id,
                   'pharmacy'::varchar AS section,
                   (pm.name ->> 'en_US')::varchar AS payment_method,
                   NULL::integer AS patient_name,
                   o.name AS reference,
                   p.amount AS amount
              FROM pos_payment p
              JOIN pos_order o ON o.id = p.pos_order_id
         LEFT JOIN pos_payment_method pm ON pm.id = p.payment_method_id
             WHERE COALESCE(p.amount, 0) <> 0
               AND o.state IN ('paid', 'done', 'invoiced')
        """
