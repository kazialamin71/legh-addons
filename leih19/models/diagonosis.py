from odoo import models, fields

class Diagonosis(models.Model):
    _name = 'diagonosis'
    _description = 'Diagonosis'

    name = fields.Char('Name')
    patient_id = fields.Char('Transaction ID', required=True)
    present_date = fields.Datetime('Test date', required=True)
    payment = fields.Selection([('zero', '00.0'), ('normal', '100'), ('ent', '200'), ('specialist', '300')], 'Amount')
    first_name = fields.Char('First Name', required=True)
    last_name = fields.Char('Last Name', required=True)
    father__name = fields.Char('Fathers Name')
    mother_name = fields.Char('Mothers Name')
    age = fields.Char('Age')
    phone = fields.Char('Phone No', required=True)
    email = fields.Char('Email')
    nid = fields.Char('NID')
    p_address = fields.Text('Peasant Address')
    per_address = fields.Text('Permanents Address')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], 'Gender')
