from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InventoryProductEntry(models.Model):
    _name = 'inventory.product.entry'
    _description = 'InventoryProductEntry'
    _order = 'id desc'

    name = fields.Char('Entry No', default='New', copy=False, readonly=True)
    invoice_no = fields.Char('Invoice/Bill No', required=True)
    invoice_date = fields.Date('Invoice/Bill Date', required=True)
    chalan_date = fields.Date('Chalan Date', required=True)
    chalan_no = fields.Char('Chalan No', required=True)
    reference_no = fields.Char('Reference No')
    total = fields.Float('Total Amount', compute='_compute_total', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Employee Name', required=True)
    grn_id = fields.Many2one('stock.picking', string='GRN NO', readonly=True, copy=False)
    grn_journal_id = fields.Many2one('account.move', string='GRN Journal', readonly=True, copy=False)
    advance_journal_id = fields.Many2one('account.move', string='Advance Journal')
    department = fields.Many2one('hr.department', string='Department')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse Location', required=True)
    inventory_product_entry_line_ids = fields.One2many('inventory.product.entry.line', 'inventory_product_entry_id', string='Inventory Requision Items', required=True)
    date = fields.Date('Entry Date', default=fields.Date.context_today)
    state = fields.Selection([('pending', 'Pending'), ('confirmed', 'Receive Product'), ('verify', 'Verified'), ('cancelled', 'Cancelled')], 'Status', default='pending', readonly=True)

    company_id = fields.Many2one(
        'res.company', string='Company', required=True, default=lambda self: self.env.company)
    payment_journal_id = fields.Many2one(
        'account.journal', string='Cash Journal', copy=False,
        domain="[('type', 'in', ('cash', 'bank')), ('company_id', '=', company_id)]",
        default=lambda self: self._default_payment_journal(),
        help='Journal the purchase is paid from. The whole entry is settled in cash '
             'on verification -- no vendor payable is created.')

    @api.model
    def _default_payment_journal(self):
        Journal = self.env['account.journal']
        domain = [('company_id', '=', self.env.company.id)]
        return (Journal.search(domain + [('type', '=', 'cash')], limit=1)
                or Journal.search(domain + [('type', '=', 'bank')], limit=1))

    @api.depends('inventory_product_entry_line_ids.total_price')
    def _compute_total(self):
        for rec in self:
            rec.total = sum(rec.inventory_product_entry_line_ids.mapped('total_price'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in ('New', False):
                vals['name'] = self.env['ir.sequence'].next_by_code('inventory.product.entry') or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------ stock
    def _vendor_location(self):
        """Where the goods come from -- the supplier location."""
        self.ensure_one()
        loc = self.warehouse_id.in_type_id.default_location_src_id
        if not loc:
            loc = self.partner_id.property_stock_supplier
        if not loc:
            loc = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1)
        if not loc:
            raise UserError(_("No vendor stock location found. Configure Inventory locations."))
        return loc

    def _create_receipt(self):
        """Receive every storable line into the selected warehouse."""
        self.ensure_one()
        ptype = self.warehouse_id.in_type_id
        if not ptype:
            raise UserError(_("Warehouse %s has no incoming operation type.") % self.warehouse_id.display_name)
        src = self._vendor_location()
        dest = ptype.default_location_dest_id or self.warehouse_id.lot_stock_id
        if not dest:
            raise UserError(_("Warehouse %s has no stock location to receive into.") % self.warehouse_id.display_name)
        move_vals = []
        for line in self.inventory_product_entry_line_ids:
            product = line.product_name
            if not product.is_storable or line.quantity <= 0:
                continue
            move_vals.append((0, 0, {
                'product_id': product.id,
                'product_uom_qty': line.quantity,
                'product_uom': product.uom_id.id,
                'location_id': src.id,
                'location_dest_id': dest.id,
                'price_unit': line.unit_price,
            }))
        if not move_vals:
            raise UserError(_(
                "No line holds a storable product with a quantity to receive. "
                "Only products tracking inventory move stock."))
        picking = self.env['stock.picking'].create({
            'picking_type_id': ptype.id,
            'partner_id': self.partner_id.id,
            'location_id': src.id,
            'location_dest_id': dest.id,
            'origin': self.name,
            'move_ids': move_vals,
        })
        picking.action_confirm()
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        picking.with_context(skip_backorder=True, skip_sms=True).button_validate()
        return picking

    # ---------------------------------------------------------------- account
    def _create_cash_entry(self):
        """Cash-basis purchase: charge each line's account, credit the cash journal."""
        self.ensure_one()
        journal = self.payment_journal_id
        if not journal:
            raise UserError(_("Set the Cash Journal this purchase is paid from."))
        credit_account = journal.default_account_id
        if not credit_account:
            raise UserError(_("Journal %s has no default account.") % journal.display_name)
        currency = self.company_id.currency_id
        ref = _('Cash purchase %s') % (self.invoice_no or self.name)
        line_vals = []
        total = 0.0
        for line in self.inventory_product_entry_line_ids:
            amount = currency.round(line.total_price)
            if not amount:
                continue
            account = line.account_id or line._purchase_account()
            if not account:
                raise UserError(_(
                    "No account set on the line for %s, and the product has none either."
                ) % line.product_name.display_name)
            line_vals.append((0, 0, {
                'name': line.product_name.display_name,
                'account_id': account.id,
                'partner_id': self.partner_id.id,
                'debit': amount,
                'credit': 0.0,
            }))
            total += amount
        if not line_vals:
            raise UserError(_("Nothing to pay -- every line totals zero."))
        line_vals.append((0, 0, {
            'name': ref,
            'account_id': credit_account.id,
            'partner_id': self.partner_id.id,
            'debit': 0.0,
            'credit': total,
        }))
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'company_id': self.company_id.id,
            'date': self.invoice_date or self.date or fields.Date.context_today(self),
            'ref': ref,
            'line_ids': line_vals,
        })
        move.action_post()
        return move

    # ---------------------------------------------------------------- buttons
    def action_receive_product(self):
        for rec in self:
            if rec.state != 'pending':
                raise UserError(_("Only a pending entry can receive products."))
            if not rec.inventory_product_entry_line_ids:
                raise UserError(_("Add at least one product line."))
            rec.grn_id = rec._create_receipt()
            rec.state = 'confirmed'
        return True

    def action_verify(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_("Receive the products before verifying the entry."))
            if not rec.grn_journal_id:
                rec.grn_journal_id = rec._create_cash_entry()
            rec.state = 'verify'
        return True

    def action_cancel(self):
        for rec in self:
            if rec.grn_id and rec.grn_id.state == 'done':
                raise UserError(_(
                    "Receipt %s is already validated. Return it in Inventory before "
                    "cancelling this entry."
                ) % rec.grn_id.display_name)
            if rec.grn_journal_id and rec.grn_journal_id.state == 'posted':
                raise UserError(_(
                    "Journal entry %s is posted. Reverse it before cancelling this entry."
                ) % rec.grn_journal_id.display_name)
            rec.state = 'cancelled'
        return True

    def action_draft(self):
        for rec in self:
            if rec.state != 'cancelled':
                raise UserError(_("Only a cancelled entry can be set back to pending."))
            rec.state = 'pending'
        return True

    def action_view_grn(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Receipt'),
            'res_model': 'stock.picking',
            'res_id': self.grn_id.id,
            'view_mode': 'form',
        }

    def action_view_journal(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entry'),
            'res_model': 'account.move',
            'res_id': self.grn_journal_id.id,
            'view_mode': 'form',
        }
