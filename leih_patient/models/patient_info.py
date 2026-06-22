import re
from datetime import date

from odoo import api, fields, models


class PatientInfo(models.Model):
    """Link a patient to a res.partner (1:1, patient is the master).

    The partner is the accounting / POS / statement identity; existing
    patient.info-based flows are unchanged. Sync is one-way (patient -> partner)
    for a few identity fields only."""
    _inherit = 'patient.info'

    partner_id = fields.Many2one(
        'res.partner', string='Contact (Partner)',
        ondelete='restrict', copy=False, readonly=True, index=True,
        help='Accounting / POS contact for this patient. Created automatically.')

    # --- Date of birth <-> Age ---
    # ``age`` (defined on leih19.patient.info as a Char) stays the canonical value
    # because it is reused as a related field on prescriptions / bills. We add a
    # real date of birth and keep the two in sync both ways via onchange.
    date_of_birth = fields.Date('Date of Birth')
    age_estimated = fields.Boolean(
        'Age Estimated', readonly=True, copy=False,
        help='The age was entered manually, so the date of birth is an estimate '
             '(1 January of the computed birth year).')

    @staticmethod
    def _years_since(dob):
        """Whole years between ``dob`` (a date) and today."""
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    @staticmethod
    def _age_to_int(age_str):
        """Leading integer of the free-text age field, or None."""
        if not age_str:
            return None
        match = re.match(r'\s*(\d+)', age_str)
        return int(match.group(1)) if match else None

    @api.onchange('date_of_birth')
    def _onchange_date_of_birth(self):
        for rec in self:
            if rec.date_of_birth:
                rec.age = str(rec._years_since(rec.date_of_birth))
                rec.age_estimated = False

    @api.onchange('age')
    def _onchange_age(self):
        for rec in self:
            years = rec._age_to_int(rec.age)
            if years is None:
                continue
            # Only back-calculate a birth date when none is set yet, or the set
            # one no longer matches the typed age. Avoids fighting a real DOB.
            if not rec.date_of_birth or rec._years_since(rec.date_of_birth) != years:
                rec.date_of_birth = date(date.today().year - years, 1, 1)
                rec.age_estimated = True

    # patient fields pushed to the partner
    _SYNC_FIELDS = ('name', 'mobile', 'address', 'patient_id')

    def _partner_base_vals(self):
        self.ensure_one()
        return {
            'name': self.name or 'Patient',
            # res.partner in Odoo 19 has only 'phone' (no 'mobile').
            'phone': self.mobile or False,
            'street': self.address or False,
            'ref': self.patient_id or False,
        }

    def _ensure_partner(self):
        Partner = self.env['res.partner']
        tag = self.env.ref('leih_patient.partner_category_patient', raise_if_not_found=False)
        for rec in self:
            if rec.partner_id:
                continue
            vals = rec._partner_base_vals()
            vals.update({'company_type': 'person', 'customer_rank': 1})
            if tag:
                vals['category_id'] = [(4, tag.id)]
            rec.partner_id = Partner.create(vals)

    def _sync_partner(self):
        for rec in self.filtered('partner_id'):
            rec.partner_id.write(rec._partner_base_vals())

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ensure_partner()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in self._SYNC_FIELDS):
            self._ensure_partner()
            self._sync_partner()
        return res

    def action_open_partner(self):
        self.ensure_one()
        self._ensure_partner()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Partner',
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def _backfill_partners(self):
        self.search([('partner_id', '=', False)])._ensure_partner()
        return True
