from odoo import api, fields, models


class ProductTemplate(models.Model):
    """Two things a pharmacy needs on a medicine: who it comes from, and what it is.

    The supplier is a plain field next to Odoo's vendor pricelist rather than a
    replacement for it. The pricelist answers "what does it cost from whom", which
    is a purchasing question; this answers "whose product is this", which is how a
    storekeeper thinks about a shelf, and it is what supplier-wise stock and the
    supplier-filtered purchase order are read from.
    """
    _inherit = 'product.template'

    medicine_generic_id = fields.Many2one(
        'medicine.generic', string='Generic (Molecule)', index=True,
        help='The molecule this brand contains. Napa, Ace and Xpa all point at '
             'Paracetamol, which is what lets the counter find one when asked '
             'for another.')
    # Denormalised so the POS can search on it: the POS loads plain fields, and
    # pulling a whole extra model into the session just to read one name would
    # cost every cashier the load time.
    medicine_generic_name = fields.Char(
        related='medicine_generic_id.name', string='Generic Name',
        store=True, index=True, readonly=True)
    therapeutic_class = fields.Char(
        related='medicine_generic_id.therapeutic_class', readonly=True)

    supplier_id = fields.Many2one(
        'res.partner', string='Supplier', index=True,
        domain="[('supplier_rank', '>', 0)]",
        help='Default supplier for this item. Used to filter the product list on '
             'a purchase order and to report stock supplier by supplier.')

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Hand the generic name to the POS so the search box can match on it."""
        fields_list = super()._load_pos_data_fields(config_id)
        if 'medicine_generic_name' not in fields_list:
            fields_list.append('medicine_generic_name')
        return fields_list

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        """Let a generic name find the brands that contain it.

        Typing "paracetamol" into any product field - a purchase order line, a
        requisition, a prescription - should offer Napa, Ace and Xpa, because
        that is how the drug is asked for.

        Appended to the normal result rather than merged into the search domain,
        so an exact brand match still sorts first; a cashier typing "Napa" wants
        Napa at the top, not buried among every other paracetamol.

        Positive operators only: a negative one means "everything except", and
        widening that set would hide products rather than reveal them.
        """
        results = super().name_search(name, domain=domain, operator=operator, limit=limit)
        if not name or operator not in ('ilike', 'like', '=ilike', '=like', '='):
            return results
        remaining = (limit - len(results)) if limit else None
        if remaining is not None and remaining <= 0:
            return results
        extra = self.search_fetch(
            list(domain or []) + [
                ('medicine_generic_name', operator, name),
                ('id', 'not in', [r[0] for r in results]),
            ],
            ['display_name'], limit=remaining)
        return results + [(r.id, r.display_name) for r in extra.sudo()]


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        """Same generic-name reach on the variant, which is what most pickers use."""
        results = super().name_search(name, domain=domain, operator=operator, limit=limit)
        if not name or operator not in ('ilike', 'like', '=ilike', '=like', '='):
            return results
        remaining = (limit - len(results)) if limit else None
        if remaining is not None and remaining <= 0:
            return results
        extra = self.search_fetch(
            list(domain or []) + [
                ('medicine_generic_name', operator, name),
                ('id', 'not in', [r[0] for r in results]),
            ],
            ['display_name'], limit=remaining)
        return results + [(r.id, r.display_name) for r in extra.sudo()]

    @api.model
    def _load_pos_data_fields(self, config):
        fields_list = super()._load_pos_data_fields(config)
        if 'medicine_generic_name' not in fields_list:
            fields_list.append('medicine_generic_name')
        return fields_list
