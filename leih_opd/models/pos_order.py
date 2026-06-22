from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    prescription_id = fields.Many2one(
        'doctor.prescription', string='Prescription',
        help='Prescription this pharmacy order was dispensed against.')


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def get_prescription_lines_for_pos(self, partner_id):
        """Return dispensable medicine lines for a partner's latest prescription.

        Consumed by the (forthcoming) POS "Load Prescription" button. Only
        products that are available in POS are returned.
        """
        presc = self.env['doctor.prescription'].search(
            [('patient_id.partner_id', '=', partner_id)], order='id desc', limit=1)
        if not presc:
            return {'prescription_id': False, 'lines': []}
        lines = [{
            'product_id': line.product_id.id,
            'qty': 1,
            'name': line.medicine_name,
        } for line in presc.medicine_line_ids
            if line.product_id and line.product_id.available_in_pos]
        return {'prescription_id': presc.id, 'lines': lines}
