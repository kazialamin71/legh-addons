from odoo import models, fields

class DiagnosisSticker(models.Model):
    _name = 'diagnosis.sticker'
    _description = 'DiagnosisSticker'

    name = fields.Char('No #')
    full_name = fields.Char('Name')
    bill_register_id = fields.Many2one('bill.register', string='Bill register')
    admission_id = fields.Many2one('leih.admission', string='Admission ID')
    general_admission_id = fields.Many2one('hospital.admission', string='Admission ID')
    department_id = fields.Char('Department')
    doctor_id = fields.Many2one('doctors.profile', string='Checked By')
    test_id = fields.Many2one('examination.entry', string='Test Name')
    sticker_line_id = fields.One2many('diagnosis.sticker.line', 'sticker_id')
    state = fields.Selection([('cancel', 'Cancelled'), ('sample', 'Sample'), ('lab', 'Lab'), ('done', 'Done'), ('delivered', 'Delivered'), ('indoor', 'Indoor')], 'Status', required=True, readonly=True, copy=False)
