from odoo import api, fields, models


class HospitalAdmissionCharge(models.Model):
    """The ward side of the split.

    ``provider_id`` already records who performed the service, so a procedure
    charge names its own doctor. Everything else on an admission -- beds,
    oxygen, consumables -- falls back to the admitting doctor.
    """
    _name = 'hospital.admission.charge'
    _inherit = ['hospital.admission.charge', 'team.charge.mixin']

    charge_item_id = fields.Many2one(
        'admission.charge.item', string='Charge Item', index=True, readonly=True,
        help='The ward catalogue item this charge was billed from. Recorded so '
             "the doctor's share configured there can be applied; diagnostic "
             'charges use item_id instead.')

    @api.model_create_multi
    def create(self, vals_list):
        """Resolve the ward catalogue item *before* the record exists.

        It used to be backfilled after ``_rebuild_charges`` had already created
        the charges, which meant every stored team field was first computed with
        no item to read a share from -- landing on zero -- and only corrected on
        a later recompute. That is what made Calculate Payable need pressing
        two or three times before the doctor's share appeared.
        """
        Line = self.env['hospital.admission.line']
        wanted = {v['source_res_id'] for v in vals_list
                  if not v.get('charge_item_id')
                  and v.get('source_model') == 'hospital.admission.line'
                  and v.get('source_res_id')}
        item_by_line = {}
        if wanted:
            for line in Line.browse(sorted(wanted)).exists():
                if line.name:
                    item_by_line[line.id] = line.name.id
        for vals in vals_list:
            if vals.get('charge_item_id'):
                continue
            item_id = item_by_line.get(vals.get('source_res_id'))
            if item_id and vals.get('source_model') == 'hospital.admission.line':
                vals['charge_item_id'] = item_id
        return super().create(vals_list)

    def _team_item(self):
        """Whichever catalogue this charge actually came from.

        Ward charges are billed from admission.charge.item and never set
        item_id, so looking only at the diagnostic catalogue would leave every
        bed, ICU and procedure charge splitting nothing. Both models carry the
        same two fields, so the caller does not care which it gets.
        """
        self.ensure_one()
        return self.charge_item_id or self.item_id

    def _team_default_provider(self):
        self.ensure_one()
        return self.provider_id or self.admission_id.admitting_doctor

    def _team_gross(self):
        self.ensure_one()
        return (self.qty or 0.0) * (self.unit_price or 0.0)

    def _team_net(self):
        self.ensure_one()
        return self.total_amount or 0.0

    def _team_qty(self):
        self.ensure_one()
        return self.qty or 0.0

    def _team_document(self):
        self.ensure_one()
        return self.admission_id

    @api.depends('provider_id', 'admission_id.admitting_doctor')
    def _compute_team_provider_id(self):
        return super()._compute_team_provider_id()

    @api.depends('item_id', 'charge_item_id', 'team_provider_id')
    def _compute_team_share_rule(self):
        return super()._compute_team_share_rule()

    @api.depends('qty', 'unit_price', 'discount', 'total_amount',
                 'team_share_method', 'team_share_value')
    def _compute_team_amount(self):
        return super()._compute_team_amount()

    @api.depends('total_amount', 'team_amount')
    def _compute_hospital_amount(self):
        return super()._compute_hospital_amount()

    @api.depends('team_provider_id', 'item_id', 'charge_item_id')
    def _compute_team_unassigned(self):
        return super()._compute_team_unassigned()
