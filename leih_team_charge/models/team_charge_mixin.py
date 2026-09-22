from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

SHARE_METHODS = [
    ('none', 'No doctor share'),
    ('percent', 'Percent of the line'),
    ('fixed', "Doctor takes a flat amount"),
    ('hospital_fixed', 'Hospital keeps a flat amount'),
]

# The first three fix the *doctor's* side and leave the hospital the remainder.
# `hospital_fixed` turns that around: the hospital's cut is the constant and the
# doctor takes whatever is left, which is how a dressing works when the hospital
# charges a fixed facility fee and the doctor sets their own fee on top -- 3,000
# and 4,000 dressings both leave the hospital 1,000.
HOSPITAL_FIXED = 'hospital_fixed'


class TeamChargeMixin(models.AbstractModel):
    """The hospital/doctor split of a single charge.

    Mixed into both charge carriers -- ``hospital.admission.charge`` and
    ``bill.register.line`` -- because a dressing has to split the same way on a
    ward as it does at an outpatient counter, and two copies of this arithmetic
    would drift apart within a month.

    Each carrier supplies three things and inherits everything else:
    ``_team_item()`` (the catalogue item the default comes from),
    ``_team_default_provider()`` (whose share it is) and the two bases.
    """
    _name = 'team.charge.mixin'
    _description = 'Hospital / Doctor Charge Split'

    team_provider_id = fields.Many2one(
        'doctors.profile', string='Share To', index=True,
        compute='_compute_team_provider_id', store=True, readonly=False,
        help="Whose share this is. Defaults to the doctor on the line, then the "
             "admitting doctor. They divide it among their team themselves.")
    # Neither `default=` nor `required=`, both deliberately:
    #   a default on a stored computed field wins over the compute at create
    #   time, so every line stayed at "no doctor share" whatever the item said;
    #   required makes the column NOT NULL, and the compute only runs after the
    #   INSERT, so the insert itself fails.
    # The compute always assigns a value, so neither is needed.
    team_share_method = fields.Selection(
        SHARE_METHODS, string='Share Basis',
        compute='_compute_team_share_rule', store=True, readonly=False)
    team_share_value = fields.Float(
        'Share Rate', compute='_compute_team_share_rule', store=True, readonly=False,
        help="A percentage of the line when the basis is percent; otherwise an "
             "amount per unit. Note that for \"Hospital keeps a flat amount\" "
             "the figure is the hospital's keep, not the doctor's share.")
    team_amount = fields.Float(
        "Doctor's Share", compute='_compute_team_amount', store=True, readonly=False,
        help='Collected from the patient but owed to the doctor. Never hospital '
             'income. Overtype it to settle a one-off differently.')
    # Its own compute, deliberately NOT shared with team_amount. Two stored
    # fields on one compute method break the moment the editable one is written
    # directly: Odoo treats the compute as satisfied and skips it, so the other
    # field is silently left NULL. That is exactly what happened -- the web
    # client posts team_amount on every save, and hospital_amount never got a
    # value, so nothing ever reached the ledger.
    hospital_amount = fields.Float(
        "Hospital's Share", compute='_compute_hospital_amount', store=True,
        help='What the hospital actually earns from this line. Always the line '
             'total less the doctor\'s share, so the two halves cannot drift.')
    team_settlement_id = fields.Many2one(
        'team.charge.settlement', string='Last Settled By', readonly=True,
        copy=False, index=True, ondelete='set null')
    # A share can be handed over in instalments -- the counter pays what the
    # patient's money covers and the rest waits -- so what has been paid is an
    # amount, not a flag. The flag is derived from it.
    team_paid = fields.Float(
        'Paid to Doctor', readonly=True, copy=False,
        help='How much of this share has actually been handed over at the '
             'counter, across all settlements.')
    # Three amounts, and the invariant paid <= entitled <= amount. Each doctor's
    # payable balance is exactly sum(entitled) - sum(paid) over their charges,
    # so the ledger and the charge rows can always be reconciled to each other.
    team_entitled = fields.Float(
        'Recognised as Payable', readonly=True, copy=False,
        help="How much of this share has been credited to the doctor's payable "
             'account -- at final settlement, or earlier if the counter paid the '
             'doctor before then.')
    team_due = fields.Float(
        'Still Owed to Doctor', compute='_compute_team_due', store=True)
    team_settled = fields.Boolean(
        'Fully Paid', compute='_compute_team_settled', store=True)
    team_unassigned = fields.Boolean(
        'Share Not Assigned', compute='_compute_team_unassigned', store=True,
        help="The item carries a doctor's share but no doctor is named, so the "
             'hospital is keeping the whole charge. Name the doctor to apply it.')

    # ------------------------------------------------------------------
    # Supplied by each carrier
    # ------------------------------------------------------------------
    def _team_item(self):
        """The catalogue item whose configuration seeds this line."""
        self.ensure_one()
        return self.env['examination.entry']

    def _team_default_provider(self):
        """Whose share this is when nobody has said otherwise."""
        self.ensure_one()
        return self.env['doctors.profile']

    def _team_gross(self):
        """Line value *before* discount -- the base a percentage applies to."""
        self.ensure_one()
        return 0.0

    def _team_net(self):
        """Line value after discount -- what the patient is actually charged."""
        self.ensure_one()
        return 0.0

    def _team_qty(self):
        self.ensure_one()
        return 1.0

    def _team_document(self):
        """The bill or admission this charge sits on."""
        self.ensure_one()
        return self.env['bill.register']

    def _team_paid_ratio(self):
        """How much of the parent document the patient has actually paid, 0..1.

        Everything collected is split in this same proportion, so a doctor's
        share of a half-paid bill is half collected -- never all of it, and
        never none of it.
        """
        self.ensure_one()
        doc = self._team_document()
        if not doc:
            return 0.0
        total = doc.grand_total or 0.0
        if total <= 0:
            return 0.0
        return min(max((doc.paid or 0.0) / total, 0.0), 1.0)

    def _team_patient_paid(self):
        """True once the patient has cleared the document in full."""
        self.ensure_one()
        return self._team_paid_ratio() >= 0.9999

    def _team_collected(self):
        """The doctor's share of what has actually been collected so far."""
        self.ensure_one()
        return (self.team_amount or 0.0) * self._team_paid_ratio()

    def _team_settlement_line_vals(self, settlement_id, amount):
        """How this carrier appears on a payout document."""
        self.ensure_one()
        field = ('charge_id' if self._name == 'hospital.admission.charge'
                 else 'bill_line_id')
        return {
            'settlement_id': settlement_id,
            field: self.id,
            'description': self._team_description(),
            'owed': self.team_amount,
            'already_paid': self.team_paid,
            'amount': amount,
        }

    def _team_description(self):
        """What this charge is called on a payout document."""
        self.ensure_one()
        return self.display_name

    # ------------------------------------------------------------------
    def _compute_team_unassigned(self):
        """Flag the one mistake this design can silently absorb.

        A share falls back to zero when nobody is named, rather than blocking
        the bill. That is the right behaviour at a busy counter, but it means a
        configured item can quietly earn the doctor nothing. This makes that
        state visible instead of leaving it to be discovered at settlement.
        """
        for rec in self:
            item = rec._team_item()
            rec.team_unassigned = bool(
                not rec.team_provider_id and item
                and item.team_share_method not in (False, 'none'))

    @api.depends('team_amount', 'team_paid')
    def _compute_team_due(self):
        for rec in self:
            rec.team_due = max((rec.team_amount or 0.0) - (rec.team_paid or 0.0), 0.0)

    @api.depends('team_amount', 'team_paid')
    def _compute_team_settled(self):
        for rec in self:
            rec.team_settled = (rec.team_amount or 0.0) > 0 and \
                (rec.team_paid or 0.0) >= (rec.team_amount or 0.0) - 0.005

    def _compute_team_provider_id(self):
        for rec in self:
            if not rec.team_provider_id:
                rec.team_provider_id = rec._team_default_provider()

    def _compute_team_share_rule(self):
        """Seed the basis and rate from the item, then from the doctor.

        Only ever fills a blank. Once someone has set a basis on the line, a
        later edit elsewhere must not silently move the money.
        """
        for rec in self:
            if rec.team_share_method and rec.team_share_method != 'none':
                # Someone has already decided on this line; a later edit to the
                # item must not silently move money that was agreed.
                continue
            item = rec._team_item()
            if item and item.team_share_method and item.team_share_method != 'none':
                rec.team_share_method = item.team_share_method
                rec.team_share_value = item.team_share_value
                continue
            doctor = rec.team_provider_id
            if doctor and doctor.default_team_method and doctor.default_team_method != 'none':
                rec.team_share_method = doctor.default_team_method
                rec.team_share_value = doctor.default_team_value
            else:
                rec.team_share_method = 'none'
                rec.team_share_value = 0.0

    def _compute_team_amount(self):
        """Doctor's share first, hospital's by subtraction.

        Subtraction, never a second independent rounding -- otherwise a
        percentage of an odd amount leaves the two halves not summing to the
        total, and every reconciliation is then out by a taka.

        The percentage applies to the *gross*, so a goodwill discount comes out
        of the hospital's share rather than quietly reducing a fee the doctor
        already agreed. The clamp stops a discount deep enough to make the
        hospital's share negative.
        """
        for rec in self:
            net = rec._team_net()
            if not rec.team_provider_id:
                # Nobody to owe it to, so the hospital keeps the lot. Naming a
                # doctor later fills the share in; blocking the bill over it
                # would stop the counter dead for a configuration detail.
                rec.team_amount = 0.0
                continue
            rate = rec.team_share_value or 0.0
            qty = rec._team_qty() or 0.0
            if rec.team_share_method == 'percent':
                team = rec._team_gross() * rate / 100.0
            elif rec.team_share_method == 'fixed':
                team = rate * qty
            elif rec.team_share_method == HOSPITAL_FIXED:
                # The rate is the *hospital's* keep, not the doctor's. Whatever
                # the line is worth above that belongs to the doctor, so the
                # same setting handles a 3,000 and a 4,000 dressing.
                team = net - rate * qty
            else:
                team = 0.0
            # Clamped both ways: a line worth less than the hospital's fixed keep
            # leaves the doctor nothing rather than a negative share.
            rec.team_amount = min(max(team, 0.0), max(net, 0.0))

    def _compute_hospital_amount(self):
        """Always the remainder, so the two halves sum to the line exactly.

        Derived by subtraction rather than computed independently: a percentage
        of an odd amount rounded twice leaves the halves not adding up, and
        every reconciliation is then out by a taka. Recomputing from
        team_amount also means a hand-typed override is honoured.
        """
        for rec in self:
            rec.hospital_amount = rec._team_net() - (rec.team_amount or 0.0)

    @api.constrains('team_amount', 'team_provider_id')
    def _check_team_amount(self):
        for rec in self:
            if rec.team_amount < 0:
                raise ValidationError(_("A doctor's share cannot be negative."))
            # A credit line - a medicine return, say - is worth a negative
            # amount and carries no share at all; ``_compute_team_amount``
            # already clamps it to zero. Comparing against the raw net would
            # then read "0 is more than -2,100" and block the credit.
            if rec.team_amount > max(rec._team_net(), 0.0) + 0.01:
                raise ValidationError(_(
                    "The doctor's share (%(team)s) is more than the line is "
                    "worth (%(net)s).",
                    team=rec.team_amount, net=rec._team_net()))

    def write(self, vals):
        """Money already handed over is a fact, not an editable figure."""
        guarded = {'team_amount', 'team_provider_id', 'team_share_method',
                   'team_share_value'}
        if guarded & set(vals) and not self.env.context.get('team_settling'):
            settled = self.filtered(lambda r: (r.team_paid or 0.0) > 0.005)
            if settled:
                raise UserError(_(
                    'Part of this share has already been paid to the doctor on '
                    '%(ref)s. Cancel that settlement first, or raise an '
                    'adjusting charge.',
                    ref=settled[:1].team_settlement_id.name or '/'))
        return super().write(vals)
