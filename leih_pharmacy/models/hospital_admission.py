from odoo import _, fields, models


class HospitalAdmission(models.Model):
    _inherit = 'hospital.admission'

    pharmacy_requisition_ids = fields.One2many(
        'pharmacy.requisition', 'admission_id', string='Pharmacy Requisitions')
    pharmacy_requisition_count = fields.Integer(compute='_compute_pharmacy_req_count')

    def _compute_pharmacy_req_count(self):
        for rec in self:
            rec.pharmacy_requisition_count = len(rec.pharmacy_requisition_ids)

    def action_new_pharmacy_requisition(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pharmacy Requisition'),
            'res_model': 'pharmacy.requisition',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_admission_id': self.id},
        }

    def action_view_pharmacy_requisitions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pharmacy Requisitions'),
            'res_model': 'pharmacy.requisition',
            'view_mode': 'list,form',
            'domain': [('admission_id', '=', self.id)],
            'context': {'default_admission_id': self.id},
        }
