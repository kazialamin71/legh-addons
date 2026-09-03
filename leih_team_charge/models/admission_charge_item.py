from odoo import fields, models

from .team_charge_mixin import SHARE_METHODS


class AdmissionChargeItem(models.Model):
    """Doctor's share on the ward catalogue.

    Admission, ICU, NICU and other ward charges come from here rather than from
    ``examination.entry``, so configuring the share on the diagnostic catalogue
    alone would leave every ward charge splitting nothing.

    Same two fields, same meaning, so one rule covers a dressing whether it was
    billed at the counter or on the ward.
    """
    _inherit = 'admission.charge.item'

    team_share_method = fields.Selection(
        SHARE_METHODS, string="Doctor's Share Basis", default='none', required=True,
        help='How much of this charge belongs to the doctor rather than the '
             'hospital. Percent applies to the price before discount, so a '
             "discount comes out of the hospital's share.")
    team_share_value = fields.Float(
        "Doctor's Share Rate",
        help='A percentage when the basis is percent, otherwise an amount per '
             'unit. For "Hospital keeps a flat amount" the figure is the '
             "hospital's keep, not the doctor's share.")
