from odoo import models, fields

class DiagnosisStickerLine(models.Model):
    _name = 'diagnosis.sticker.line'
    _description = 'DiagnosisStickerLine'

    test_name = fields.Char('Name')
    sticker_id = fields.Many2one('diagnosis.sticker', string='ID')
    result = fields.Char('Result')
    ref_value = fields.Char('Reference Value')
    bold = fields.Boolean('Bold')
    group_by = fields.Boolean('Group By')
    remarks = fields.Char('Remarks')
