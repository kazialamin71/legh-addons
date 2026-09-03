from odoo import fields, models

from .team_charge_mixin import SHARE_METHODS


class ExaminationEntry(models.Model):
    """Where a doctor's share is configured.

    Set once here and every admission charge and bill line built from this item
    picks it up, on the ward and at the counter alike. A line can still be
    overtyped, but nobody has to remember the rate.
    """
    _inherit = 'examination.entry'

    team_share_method = fields.Selection(
        SHARE_METHODS, string="Doctor's Share Basis", default='none', required=True,
        help='How much of this item belongs to the doctor rather than the '
             'hospital. Percent applies to the price before discount, so a '
             'discount comes out of the hospital\'s share.')
    team_share_value = fields.Float(
        "Doctor's Share Rate",
        help='A percentage when the basis is percent, otherwise a flat amount '
             'per unit. Example: a dressing at 2,000 with 50 percent, or with a '
             'flat 1,000, both leave the hospital 1,000.')
