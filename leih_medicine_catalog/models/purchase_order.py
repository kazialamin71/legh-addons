from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    show_all_products = fields.Boolean(
        'Show All Products', default=False,
        help="Off: the product list on this order only offers what this supplier "
             "supplies - their own items and anything on their vendor pricelist. "
             "On: every purchasable product is offered, for the one-off buy from "
             "a supplier who does not normally carry the item.")


class ProductProduct(models.Model):
    """Supplier-driven product picking on a purchase order.

    Done through the context rather than a computed ``allowed_product_ids``
    many2many: the alternative has to materialise every purchasable product into
    the form's data just to say "no filter", which on a pharmacy catalogue of a
    few thousand items is a page load the buyer pays for on every order. A
    context flag lets the filter stay a WHERE clause.
    """
    _inherit = 'product.product'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        supplier = self.env.context.get('po_filter_supplier_id')
        if supplier and not self.env.context.get('po_show_all_products'):
            domain = list(domain or []) + [
                '|',
                ('product_tmpl_id.supplier_id', '=', supplier),
                ('seller_ids.partner_id', '=', supplier),
            ]
        return super()._search(domain, offset=offset, limit=limit, order=order, **kwargs)
