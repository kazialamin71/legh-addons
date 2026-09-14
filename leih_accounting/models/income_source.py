"""Where a charge's income account comes from when no catalogue item carries one.

Bed days and doctor visits are the two charges the catalogue cannot answer for:
a bed belongs to ``hospital.bed`` and a visit to ``doctors.profile``, neither of
which had an account field. Without one, an ICU day and a general bed day are
indistinguishable to the ledger the moment two beds of the same type charge to
different heads -- and a hospital that splits NICU income from ICU income sooner
or later wants exactly that.

So each gets an optional account of its own, and the charge stamps it at
creation. Left blank -- the normal case -- the charge still resolves through the
service-type map, which is enough as long as every ICU bed posts to the same
head.
"""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BedCategory(models.Model):
    """Where ward income is normally configured.

    The category is what a hospital actually prices and reports by -- AC Cabin,
    VIP Cabin, General Bed, ICU, NICU -- and indoor_management already cascades
    the per-day charge down category > ward > bed. The income head follows the
    same three levels for the same reason: set it once on 'AC Cabin' and every
    cabin in every ward of that class credits the right account, with the ward
    and the individual bed there for the exceptions.
    """
    _inherit = 'bed.category'

    income_account_id = fields.Many2one(
        'account.account', string='Income Account',
        domain="[('account_type', '=', 'income')]",
        help='Revenue head credited for days spent in beds of this category. '
             'The usual place to set ward income. Blank falls back to the bed '
             "type's row in the service-type map.")


class HospitalWard(models.Model):
    _inherit = 'hospital.ward'

    income_account_id = fields.Many2one(
        'account.account', string='Income Account',
        domain="[('account_type', '=', 'income')]",
        help='Overrides the category account for beds in this ward/room. Blank '
             'uses the category.')


class HospitalBed(models.Model):
    _inherit = 'hospital.bed'

    income_account_id = fields.Many2one(
        'account.account', string='Income Account',
        domain="[('account_type', '=', 'income')]",
        help='Overrides the ward and category account for this one bed. Blank '
             'uses the ward, then the category, then the account mapped to the '
             'bed type (General / Cabin / ICU / NICU / HDU).')

    def get_effective_income_account(self):
        """Bed > ward > category, exactly like ``get_effective_charge``.

        Deliberately the same order as the rate: whoever decided that this ward
        charges differently almost always means it earns differently too, and
        two cascades that disagree would be a trap.
        """
        self.ensure_one()
        return (self.income_account_id
                or self.ward_id.income_account_id
                or self.category_id.income_account_id
                or self.env['account.account'])


class DoctorsProfile(models.Model):
    _inherit = 'doctors.profile'

    income_account_id = fields.Many2one(
        'account.account', string='Fee Income Account',
        domain="[('account_type', '=', 'income')]",
        help="Revenue head credited for this doctor's indoor visit fees. Blank "
             "uses the account mapped to the Doctor Fee service type.")


class HospitalAdmissionCharge(models.Model):
    """Stamp the income head on the charge, so it is visible before release."""
    _inherit = 'hospital.admission.charge'

    effective_income_account_id = fields.Many2one(
        'account.account', string='Posts To', compute='_compute_effective_income_account',
        help='The head this charge will actually credit at final settlement, '
             'after the catalogue item, the bed/doctor account, the service-type '
             'map and the default income account have all been tried.')

    # ------------------------------------------------------------- resolution
    def _source_income_account(self):
        """The account the thing being charged for points at, if any.

        Catalogue item first (diagnostics and ward charges both have one), then
        the bed the day was spent in, then the doctor who visited.
        """
        self.ensure_one()
        account = self._catalogue_account()
        if account:
            return account
        if self.source_model == 'hospital.bed.line' and self.source_res_id:
            line = self.env['hospital.bed.line'].browse(self.source_res_id).exists()
            if line.bed_no:
                account = line.bed_no.get_effective_income_account()
                if account:
                    return account
        if self.provider_id.income_account_id:
            return self.provider_id.income_account_id
        return self.env['account.account']

    def _stamp_income_account(self):
        """Fill a blank income account from the source. Never overwrites one
        that is already set -- a hand-picked head on a line has to survive."""
        for rec in self:
            if rec.income_account_id:
                continue
            account = rec._source_income_account()
            if account:
                rec.income_account_id = account

    @api.model_create_multi
    def create(self, vals_list):
        charges = super().create(vals_list)
        charges._stamp_income_account()
        return charges

    @api.depends('income_account_id', 'service_type', 'provider_id', 'source_model')
    def _compute_effective_income_account(self):
        # search, not _get(): a compute must not create the settings record, and
        # on a database with posting switched off there may not be one.
        cfg = self.env['leih.accounting.config'].sudo().search(
            [('company_id', '=', self.env.company.id)], limit=1)
        for rec in self:
            rec.effective_income_account_id = (
                cfg._charge_income_account(rec) if cfg else rec.income_account_id)

    @api.constrains('income_account_id')
    def _check_income_account_not_rollup(self):
        Config = self.env['leih.accounting.config']
        for rec in self:
            if rec.income_account_id and Config._is_rollup(rec.income_account_id):
                raise ValidationError(_(
                    '%(account)s is a roll-up head with children under it. Pick '
                    'one of its child accounts for this charge.',
                    account=rec.income_account_id.display_name))

    @api.onchange('provider_id')
    def _onchange_provider_account(self):
        for rec in self:
            if rec.provider_id.income_account_id and not rec.income_account_id:
                rec.income_account_id = rec.provider_id.income_account_id
