from odoo import models, fields

class CommissionConfigurationLine(models.Model):
    """One scoped rule inside an MOU.

    A line says *what it covers* and *how much it pays*. The scope fields are
    checked most-specific first, so an MOU can carry a blanket "30% on
    diagnostics" alongside "but this one test pays a flat 200" without the two
    fighting:

        test_id  >  charge_item_id  >  department_id  >  service_type

    ``service_type`` is the bucket an admitted patient's charges are filed
    under in ``hospital.admission.charge`` -- bed, ICU, NICU, diagnostic,
    medicine... It is how a ward charge gets a rule at all: NICU bed charges
    come from ``hospital.bed.line`` and carry no ``examination.entry`` and no
    income unit, so nothing but the bucket identifies them.
    """
    _name = 'commission.configuration.line'
    _description = 'CommissionConfigurationLine'

    commission_configuration_line_ids = fields.Many2one('commission.configuration', string='Commission Configuration ID')
    department_id = fields.Many2one('diagnosis.department', string='Department')
    test_id = fields.Many2one('examination.entry', string='Test Name')
    charge_item_id = fields.Many2one(
        'admission.charge.item', string='Admission Charge Item',
        help="Ward/admission charge this rule covers (bed, ICU, NICU, oxygen...). "
             "These are catalogued separately from diagnostic tests.")
    service_type = fields.Selection(
        selection=lambda self: self.env['hospital.admission.charge']._fields['service_type'].selection,
        string='Service Type',
        help="Covers every charge an admitted patient is billed under this bucket "
             "-- e.g. 'NICU' for the NICU bed charge, 'Diagnostic' for all "
             "investigations done while admitted. Broadest scope: a test or "
             "charge item rule overrides it.")
    base_price_applicable = fields.Boolean('Base Price Applicable')
    applicable = fields.Boolean('Applicable', default=True)
    line_method = fields.Selection(
        [('percentage', 'Percentage / Fixed'),
         ('margin', 'Margin over Base Price')],
        string='Method', default='percentage', required=True,
        help="Percentage / Fixed: a % (and/or fixed) for this department/test.\n"
             "Margin over Base Price: referrer keeps whatever the bill exceeds the base price "
             "(e.g. base 4000, billed 5000 -> 1000).")
    base_price = fields.Float('Base Price', help="Referrer's agreed base/floor price for this test "
                                                 "(used by the 'Margin over Base Price' method).")
    fixed_amount = fields.Float('Fixed Amount')
    variance_amount = fields.Float('Amount (%)')
    test_price = fields.Float('Test Fee')
    est_commission_amount = fields.Float('Commission Amount')
    max_commission_amount = fields.Float('Max Commission Amount')

    def _scope_label(self):
        """What this line covers, for the form and for error messages."""
        self.ensure_one()
        if self.test_id:
            return self.test_id.display_name
        if self.charge_item_id:
            return self.charge_item_id.display_name
        if self.department_id:
            return self.department_id.name
        if self.service_type:
            labels = dict(self._fields['service_type']._description_selection(self.env))
            return labels.get(self.service_type, self.service_type)
        return 'Everything (overall rule)'

    def _compute_display_name(self):
        for rec in self:
            rec.display_name = rec._scope_label()
