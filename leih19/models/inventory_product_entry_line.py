from odoo import api, fields, models


class InventoryProductEntryLine(models.Model):
    _name = 'inventory.product.entry.line'
    _description = 'InventoryProductEntryLine'

    name = fields.Char('Inventory Requisition Line Id')
    inventory_product_entry_id = fields.Many2one(
        'inventory.product.entry', string='Inventory Entry ID', ondelete='cascade', index=True)
    product_name = fields.Many2one('product.product', string='Product Name', required=True)
    account_id = fields.Many2one('account.account', string='Account')
    quantity = fields.Float('Quantity', default=1.0)
    unit_price = fields.Float('Unit Price')
    total_price = fields.Float('Total Price', compute='_compute_total_price', store=True, readonly=True)

    @api.depends('quantity', 'unit_price')
    def _compute_total_price(self):
        for rec in self:
            rec.total_price = (rec.quantity or 0.0) * (rec.unit_price or 0.0)

    @api.onchange('product_name')
    def _onchange_product_name(self):
        for rec in self:
            if not rec.product_name:
                continue
            if not rec.unit_price:
                rec.unit_price = rec.product_name.standard_price
            if not rec.account_id:
                rec.account_id = rec._purchase_account()

    def _purchase_account(self):
        """Account to debit when this line is paid for in cash.

        The product's expense account: the receipt itself books no accounting
        entry, so the purchase is charged here and Odoo's own stock valuation
        entries balance it against Stock Variation. Override per line with
        `account_id` to charge inventory or a department account instead.
        """
        self.ensure_one()
        if not self.product_name:
            return self.env['account.account']
        accounts = self.product_name.product_tmpl_id.get_product_accounts()
        return accounts.get('expense') or self.env['account.account']
