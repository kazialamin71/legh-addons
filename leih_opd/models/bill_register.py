from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BillRegister(models.Model):
    _inherit = 'bill.register'

    prescription_id = fields.Many2one(
        'doctor.prescription', string='From Prescription',
        domain="[('patient_id', '=', patient_name)]",
        help='Load the investigations a doctor prescribed straight into this bill.')

    def action_load_from_prescription(self):
        """Pull prescribed investigations into this bill.

        For each investigation line we use the linked billing item
        (``examination_id``); if the doctor only typed a name, we try to match
        it against the examination catalogue by name. Items already on the bill
        are skipped."""
        self.ensure_one()
        if not self.patient_name:
            raise UserError(_('Please select the patient first.'))
        presc = self.prescription_id or self.env['doctor.prescription'].search(
            [('patient_id', '=', self.patient_name.id)], order='id desc', limit=1)
        if not presc:
            raise UserError(_('No prescription found for this patient.'))
        if not presc.test_line_ids:
            raise UserError(_(
                'Prescription %s has no investigations to load.', presc.name))

        Entry = self.env['examination.entry']
        existing = self.bill_register_line_id.mapped('name')
        commands = []
        unmatched = []
        for test in presc.test_line_ids:
            entry = test.examination_id
            if not entry and test.test_name:
                entry = Entry.search([('name', '=ilike', test.test_name)], limit=1)
            if not entry:
                unmatched.append(test.test_name or _('(unnamed)'))
                continue
            if entry in existing:
                continue
            existing |= entry
            commands.append((0, 0, {
                'name': entry.id,
                'department': entry.department.name if entry.department else False,
                'product_qty': 1,
                'price': entry.rate,
                'total_amount': entry.rate,
                'assign_doctors': presc.doctor_id.id,
            }))

        if not commands:
            if unmatched:
                raise UserError(_(
                    'None of the prescribed investigations match a billing item '
                    '(examination entry):\n- %s\n\nOpen the prescription and pick '
                    'the "Investigation Item" on each line, or add matching items '
                    'under Examination Entries.', '\n- '.join(unmatched)))
            raise UserError(_(
                'All prescribed investigations are already on this bill.'))

        self.bill_register_line_id = commands
        if not self.prescription_id:
            self.prescription_id = presc
        return True
