from odoo import api, fields, models

from .blood_groups import BLOOD_GROUPS, SEXES


class BloodDonar(models.Model):
    """The donor register, given the fields a crossmatch slip has to print.

    ``blood.donar`` already existed as a list of who gave blood and when. It had
    no age, no sex and only a free-text group -- all three of which the slip
    prints -- so they were being retyped onto every crossmatch instead of being
    read off the donor. Legacy ``group`` is left alone: it holds whatever was
    typed into it historically and nothing reads it any more.
    """
    _inherit = 'blood.donar'

    age = fields.Char('Age', help='As recorded at donation, e.g. "28 Y".')
    sex = fields.Selection(SEXES, string='Sex')
    blood_group = fields.Selection(BLOOD_GROUPS, string='Blood Group (ABO/Rh)')
    donation_count = fields.Integer('Donations', compute='_compute_donation_count')

    @api.depends('doner_name')
    def _compute_donation_count(self):
        Result = self.env['examination.result']
        for rec in self:
            rec.donation_count = Result.search_count([('donor_id', '=', rec.id)]) if rec.id else 0

    @api.depends('doner_name', 'blood_group')
    def _compute_display_name(self):
        labels = dict(BLOOD_GROUPS)
        for rec in self:
            group = labels.get(rec.blood_group)
            name = rec.doner_name or rec.name or ''
            rec.display_name = '%s [%s]' % (name, group) if group and name else name
