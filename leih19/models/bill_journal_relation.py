from odoo import models, fields

class BillJournalRelation(models.Model):
    _name = 'bill.journal.relation'
    _description = 'BillJournalRelation'

    bill_journal_relation_id = fields.Many2one('bill.register', string='bill register payment')
    admission_journal_relation_id = fields.Many2one('leih.admission', string='Admission Journal')
    general_admission_journal_relation_id = fields.Many2one('hospital.admission', string='General Admission Journal')
    journal_id = fields.Integer('Journal Id')
