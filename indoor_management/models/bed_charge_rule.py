from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Fallback used when no rule is configured at all, so an un-set-up database
# still bills something sane rather than nothing.
FALLBACK_BANDS = ((2.0, 0.0), (6.0, 50.0), (0.0, 100.0))
DEFAULT_CYCLE_START_HOUR = 12
DEFAULT_CYCLE_END_HOUR = 11


class BedChargeRule(models.Model):
    """How occupancy hours turn into a day's accommodation charge.

    The thresholds used to be three module constants -- 6 hours for half a day,
    12 for a full one -- which meant "ICU charges a full day after 4 hours but
    the ward waits 6" was a code change. They are rows now.

    A rule applies to the bed categories listed on it. Exactly one rule is the
    default and covers every category that names no rule of its own, so adding a
    category never silently leaves its beds unbilled.
    """
    _name = 'bed.charge.rule'
    _description = 'Bed Charge Rule'
    _order = 'is_default desc, sequence, name'

    name = fields.Char('Rule', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    is_default = fields.Boolean(
        'Default Rule',
        help='Applies to every bed category that has no rule of its own. '
             'Exactly one rule is the default.')
    category_ids = fields.One2many(
        'bed.category', 'charge_rule_id', string='Bed Categories',
        help='Categories billed by this rule. A category can only follow one '
             'rule; assigning it here takes it off whichever rule it was on.')
    band_ids = fields.One2many(
        'bed.charge.rule.band', 'rule_id', string='Charge Bands', copy=True)

    cycle_start_hour = fields.Integer(
        'Cycle Starts At', default=DEFAULT_CYCLE_START_HOUR,
        help='Hour of the local day a billing cycle opens (0-23). 12 means a '
             'cycle runs noon to noon.')
    cycle_end_hour = fields.Integer(
        'Cycle Ends At', default=DEFAULT_CYCLE_END_HOUR,
        help='Hour the cycle closes. Setting it an hour before the start hour '
             'gives a checkout grace period -- with 12 and 11, a patient who '
             'leaves before 11:00 is not charged for that day.')
    note = fields.Char('Note')

    _sql_constraints = [
        ('cycle_start_hour_range', 'CHECK (cycle_start_hour >= 0 AND cycle_start_hour <= 23)',
         'The cycle start hour must be between 0 and 23.'),
        ('cycle_end_hour_range', 'CHECK (cycle_end_hour >= 0 AND cycle_end_hour <= 23)',
         'The cycle end hour must be between 0 and 23.'),
    ]

    @api.constrains('is_default')
    def _check_single_default(self):
        for rec in self.filtered('is_default'):
            other = self.search([('is_default', '=', True), ('id', '!=', rec.id)], limit=1)
            if other:
                raise ValidationError(_(
                    '%(other)s is already the default rule. A category with no '
                    'rule of its own has to fall to exactly one of them, so '
                    'take the default off %(other)s first.', other=other.name))

    @api.constrains('band_ids')
    def _check_bands(self):
        for rec in self:
            if not rec.band_ids:
                continue
            unbounded = rec.band_ids.filtered(lambda b: b.up_to_hours <= 0)
            if len(unbounded) > 1:
                raise ValidationError(_(
                    '%s has more than one "and above" band. Only the last band '
                    'may be left open-ended.', rec.name))
            if not unbounded:
                raise ValidationError(_(
                    '%s has no "and above" band: a stay longer than %s hours '
                    'would be charged nothing. Add a band with "Up To Hours" '
                    'left at 0 to cover everything beyond the last threshold.',
                    rec.name, max(rec.band_ids.mapped('up_to_hours'))))

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------
    @api.model
    def _for_category(self, category):
        """The rule billing a bed category: its own, else the default."""
        if category and category.charge_rule_id and category.charge_rule_id.active:
            return category.charge_rule_id
        return self.search([('is_default', '=', True)], limit=1)

    def _bands(self):
        """(upper bound in hours, fraction of a day) ascending, open-ended last.

        An unconfigured rule -- or none at all -- answers with the built-in
        fallback instead of an empty list, because an empty list would price
        every stay at zero and look exactly like a hospital that gives beds
        away.
        """
        if not self or not self.band_ids:
            return [(hours, pct / 100.0) for hours, pct in FALLBACK_BANDS]
        self.ensure_one()
        bounded = self.band_ids.filtered(lambda b: b.up_to_hours > 0).sorted('up_to_hours')
        unbounded = self.band_ids.filtered(lambda b: b.up_to_hours <= 0)[:1]
        bands = [(b.up_to_hours, b.charge_percent / 100.0) for b in bounded]
        bands.append((0.0, (unbounded.charge_percent if unbounded else 100.0) / 100.0))
        return bands

    def day_fraction(self, hours):
        """Fraction of a day's charge earned by ``hours`` of occupancy."""
        for upper, fraction in self._bands():
            if upper <= 0 or hours < upper:
                return fraction
        return 1.0

    def _cycle_hours(self):
        """(start hour, end hour) for the billing cycle, with the defaults."""
        if not self:
            return DEFAULT_CYCLE_START_HOUR, DEFAULT_CYCLE_END_HOUR
        self.ensure_one()
        return self.cycle_start_hour, self.cycle_end_hour


class BedChargeRuleBand(models.Model):
    """One "up to N hours, charge X%" row of a charge rule."""
    _name = 'bed.charge.rule.band'
    _description = 'Bed Charge Band'
    # The open-ended band is stored as 0 but reads as the last row, so it is
    # sorted by a derived flag rather than by the bound itself.
    _order = 'is_open_ended, up_to_hours'

    rule_id = fields.Many2one('bed.charge.rule', string='Rule', required=True, ondelete='cascade')
    up_to_hours = fields.Float(
        'Up To Hours', required=True,
        help='Upper bound of this band, exclusive. Leave at 0 for the final '
             '"and above" band.')
    is_open_ended = fields.Boolean(
        'And Above', compute='_compute_is_open_ended', store=True)
    charge_percent = fields.Float(
        'Charge (%)', required=True, default=100.0,
        help="Percentage of the accommodation's per-day charge billed for a "
             'stay falling in this band.')

    _sql_constraints = [
        ('charge_percent_positive', 'CHECK (charge_percent >= 0)',
         'A charge percentage cannot be negative.'),
    ]

    @api.depends('up_to_hours')
    def _compute_is_open_ended(self):
        for rec in self:
            rec.is_open_ended = rec.up_to_hours <= 0

    @api.depends('up_to_hours', 'charge_percent')
    def _compute_display_name(self):
        for rec in self:
            if rec.up_to_hours <= 0:
                bound = _('and above')
            else:
                bound = _('under %g hours', rec.up_to_hours)
            rec.display_name = '%s: %g%%' % (bound, rec.charge_percent)
