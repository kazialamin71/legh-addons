from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AdmissionChargeType(models.Model):
    """The buckets ward charges are billed under, as records rather than code.

    ``admission.charge.item.charge_type`` was a four-value Selection --
    Admission / ICU / NICU / Other -- which meant a hospital that wanted a
    "Team Charge", "Ambulance" or "OT Package" bucket had to have the code
    changed. The selection is now built from this table, so a new bucket is a
    record.

    The stored column is still the ``code``, so every existing row, view,
    filter and report keeps working; only where the list of choices comes from
    has changed.

    ``service_type`` is what ties a bucket back to the machinery that already
    exists: the charge ledger, the income-by-service-type map and the P&L all
    speak ``hospital.admission.charge.service_type``, and a new bucket has to
    say which of those it behaves like. A "Team Charge" bucket that maps to
    'admission' is billed and accounted for exactly like an admission charge but
    prints under its own heading -- which is the whole point of having it.
    """
    _name = 'admission.charge.type'
    _description = 'Admission Charge Type'
    _order = 'sequence, name'

    name = fields.Char('Charge Type', required=True, translate=True)
    code = fields.Char(
        'Code', required=True,
        help='Stored on every charge item and admission line. Changing it on a '
             'type already in use would orphan those rows, so it is read-only '
             'once anything points at it.')
    sequence = fields.Integer(default=10, help='Order in the picker and on the printed bill.')
    service_type = fields.Selection(
        selection=lambda self: self.env['hospital.admission.charge']._fields['service_type'].selection,
        string='Behaves Like', required=True, default='other',
        help='Which kind of charge this bucket is, for the charge ledger and the '
             'income-by-service-type map. Pick the closest existing kind; the '
             'bucket still prints under its own name.')
    income_account_id = fields.Many2one(
        'account.account', string='Income Account',
        domain="[('account_type', '=', 'income')]",
        help='Default revenue head for items of this type. An account on the '
             'item itself still wins; blank falls back to the service type map.')
    note = fields.Char('Note')

    _code_uniq = models.Constraint('unique (code)', 'That charge type code is already used.')

    @api.model
    def _selection(self):
        """The Selection list for ``charge_type``.

        Every type is returned, never a filtered subset: a Selection whose list
        is missing a value that rows still store renders those rows blank, so
        retiring a type has to mean deleting it (which is blocked while it is in
        use) rather than hiding it.
        """
        types = self.search([])
        return [(t.code, t.name) for t in types]

    @api.model
    def _service_type_of(self, code):
        """``service_type`` for a charge-type code, 'other' if it names nothing."""
        if not code:
            return 'other'
        return self.search([('code', '=', code)], limit=1).service_type or 'other'

    @api.constrains('code')
    def _check_code(self):
        for rec in self:
            if not (rec.code or '').strip():
                raise ValidationError(_('A charge type needs a code.'))

    def _usage_count(self):
        self.ensure_one()
        return self.env['admission.charge.item'].with_context(active_test=False).search_count(
            [('charge_type', '=', self.code)])

    @api.ondelete(at_uninstall=False)
    def _unlink_if_unused(self):
        for rec in self:
            used = rec._usage_count()
            if used:
                raise ValidationError(_(
                    '%(name)s is used by %(count)s charge item(s). Move them to '
                    'another type first -- deleting it would leave those items '
                    'with a charge type that no longer exists.',
                    name=rec.name, count=used))

    def write(self, vals):
        if 'code' in vals:
            for rec in self:
                if rec.code != vals['code'] and rec._usage_count():
                    raise ValidationError(_(
                        'The code of %s cannot be changed while charge items '
                        'still point at it.', rec.name))
        return super().write(vals)
