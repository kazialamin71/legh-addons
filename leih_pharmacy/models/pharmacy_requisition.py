from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PharmacyRequisition(models.Model):
    _name = 'pharmacy.requisition'
    _description = 'Pharmacy Requisition (IPD dispense)'
    _order = 'id desc'

    name = fields.Char('Requisition No', default='New', copy=False, readonly=True)
    admission_id = fields.Many2one(
        'hospital.admission', string='Admission', required=True, ondelete='cascade', index=True)
    patient_id = fields.Many2one(related='admission_id.patient_name', string='Patient', store=True, readonly=True)
    date = fields.Datetime('Date', default=fields.Datetime.now)
    requested_by = fields.Char('Requested By (Nurse)')

    location_id = fields.Many2one(
        'stock.location', string='Pharmacy Location', required=True,
        default=lambda self: self._default_location(),
        domain="[('usage', '=', 'internal')]",
        help='Stock location medicines are issued from.')

    line_ids = fields.One2many('pharmacy.requisition.line', 'requisition_id', string='Medicines')
    picking_ids = fields.Many2many('stock.picking', string='Stock Transfers', copy=False)
    picking_count = fields.Integer(compute='_compute_picking_count')
    charge_id = fields.Many2one(
        'hospital.admission.charge', string='Admission Charge', copy=False, readonly=True,
        help='The admission charge this requisition raised. When the medicines '
             'issued credit more than one income account there is one charge per '
             'account and this points at the first of them.')

    net_amount = fields.Float('Net Amount', compute='_compute_net_amount', store=True,
                              help='Charged to the admission = sum of (issued - returned) x price.')
    state = fields.Selection(
        [('draft', 'Draft'),
         ('issued', 'Issued'),
         ('returned', 'Returned'),
         ('cancelled', 'Cancelled')],
        default='draft', required=True, copy=False, tracking=True)

    @api.model
    def _default_location(self):
        # prefer a location named like "pharmacy", else any internal stock location
        Loc = self.env['stock.location']
        loc = Loc.search([('usage', '=', 'internal'), ('complete_name', 'ilike', 'pharmacy')], limit=1)
        if not loc:
            loc = Loc.search([('usage', '=', 'internal')], limit=1)
        return loc

    @api.depends('line_ids.subtotal')
    def _compute_net_amount(self):
        for rec in self:
            rec.net_amount = sum(rec.line_ids.mapped('subtotal'))

    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = len(rec.picking_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in ('New', False):
                vals['name'] = self.env['ir.sequence'].next_by_code('pharmacy.requisition') or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------ stock
    def _customer_location(self):
        loc = self.env['stock.location'].search([('usage', '=', 'customer')], limit=1)
        if not loc:
            raise UserError(_("No customer stock location found. Configure Inventory locations."))
        return loc

    def _picking_type(self, code):
        ptype = self.env['stock.picking.type'].search([
            ('code', '=', code),
            ('warehouse_id.company_id', '=', self.env.company.id),
        ], limit=1)
        if not ptype:
            ptype = self.env['stock.picking.type'].search([('code', '=', code)], limit=1)
        if not ptype:
            raise UserError(_("No %s operation type configured in Inventory.") % code)
        return ptype

    def _do_picking(self, moves_qty, src, dest, ptype):
        """Create, reserve and validate a transfer for [(product, qty), ...]."""
        self.ensure_one()
        move_vals = []
        for product, qty in moves_qty:
            if qty <= 0:
                continue
            move_vals.append((0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
                'product_uom': product.uom_id.id,
                'location_id': src.id,
                'location_dest_id': dest.id,
            }))
        if not move_vals:
            return self.env['stock.picking']
        picking = self.env['stock.picking'].create({
            'picking_type_id': ptype.id,
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
        self.picking_ids = [(4, picking.id)]
        return picking

    # ------------------------------------------------------------------ charge
    def _charges(self):
        """Every admission charge this requisition owns.

        Searched by source rather than read off ``charge_id``, because a
        requisition can now raise more than one charge (one per income account)
        and ``charge_id`` only ever holds the first.
        """
        self.ensure_one()
        return self.env['hospital.admission.charge'].search([
            ('source_model', '=', 'pharmacy.requisition'),
            ('source_res_id', '=', self.id),
        ])

    def _line_income_account(self, line):
        """Income account for one dispensed medicine, or blank to fall back.

        Only an account set *explicitly* on the medicine counts -- deliberately
        not ``get_product_accounts()``, which falls through to the product
        category and therefore always answers something. Letting that win would
        quietly send every dispense to the category's generic sales account and
        make the pharmacy account configured under Hospital Accounting dead
        configuration, which is the opposite of useful.

        So: a per-medicine override if someone set one, otherwise blank, which
        lets the poster resolve the 'Medicine' row of the service-type map and
        then the default income account. One place to configure, one place to
        override.
        """
        self.ensure_one()
        product = line.product_id
        if not product:
            return self.env['account.account']
        return (product.property_account_income_id
                or product.product_tmpl_id.property_account_income_id
                or self.env['account.account'])

    def _sync_charge(self):
        """Rebuild this requisition's admission charges = net amount per account.

        One charge per income account. With a single pharmacy income account
        configured -- the normal case -- that is one charge, exactly as before;
        it only splits when the medicines issued genuinely post to different
        accounts, which is the only way the general ledger can be right.

        Rebuilt rather than written in place because a return changes which
        products are still chargeable, so the set of accounts can change too.
        """
        self.ensure_one()
        Charge = self.env['hospital.admission.charge']
        buckets = {}
        for line in self.line_ids:
            subtotal = line.subtotal or 0.0
            if not subtotal:
                continue
            account = self._line_income_account(line)
            buckets.setdefault(account, 0.0)
            buckets[account] += subtotal

        self._charges().unlink()
        if not buckets:
            self.charge_id = False
            return

        multiple = len(buckets) > 1
        charges = Charge
        for account, amount in buckets.items():
            label = _('Pharmacy: %s') % self.name
            if multiple and account:
                label = '%s [%s]' % (label, account.display_name)
            charges |= Charge.create({
                'admission_id': self.admission_id.id,
                'service_type': 'medicine',
                'description': label,
                'qty': 1.0,
                'unit_price': amount,
                'discount': 0.0,
                'income_account_id': account.id if account else False,
                'date': self.date or fields.Datetime.now(),
                'source_model': 'pharmacy.requisition',
                'source_res_id': self.id,
            })
        self.charge_id = charges[:1].id

    # ------------------------------------------------------------------ buttons
    def action_issue(self):
        # A Dispenser issues (and may also create + issue their own). A plain
        # Pharmacy User (nurse) can only create -- they don't have this group.
        if not self.env.user.has_group('leih_pharmacy.group_pharmacy_dispenser'):
            raise UserError(_("Only a Pharmacy Dispenser can issue medicines."))
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only a draft requisition can be issued."))
            to_issue = [(l.product_id, l.issued_qty) for l in rec.line_ids if l.issued_qty > 0]
            if not to_issue:
                raise UserError(_("Set the issued quantity on at least one medicine."))
            rec._do_picking(to_issue, rec.location_id, rec._customer_location(),
                            rec._picking_type('outgoing'))
            for line in rec.line_ids:
                line.issued_done_qty = line.issued_qty
            rec.state = 'issued'
            rec._sync_charge()
        return True

    def action_return(self):
        """Return newly-flagged quantities (returned_qty above what was already
        returned): reverse stock + reduce the admission charge."""
        for rec in self:
            if rec.state not in ('issued', 'returned'):
                raise UserError(_("Only an issued requisition can be returned."))
            to_return = []
            for line in rec.line_ids:
                delta = (line.returned_qty or 0.0) - (line.returned_done_qty or 0.0)
                if delta < 0:
                    raise UserError(_("Returned qty cannot be reduced for %s.") % line.product_id.display_name)
                if delta > (line.issued_qty - line.returned_done_qty):
                    raise UserError(_("Cannot return more than issued for %s.") % line.product_id.display_name)
                if delta > 0:
                    to_return.append((line.product_id, delta))
            if not to_return:
                raise UserError(_("Set a higher Returned Qty on at least one line, then click Return."))
            rec._do_picking(to_return, rec._customer_location(), rec.location_id,
                            rec._picking_type('incoming'))
            for line in rec.line_ids:
                line.returned_done_qty = line.returned_qty
            all_returned = all(
                (l.returned_qty or 0.0) >= (l.issued_qty or 0.0) for l in rec.line_ids)
            rec.state = 'returned' if all_returned else 'issued'
            rec._sync_charge()
        return True

    def action_cancel(self):
        is_dispenser = self.env.user.has_group('leih_pharmacy.group_pharmacy_dispenser')
        for rec in self:
            if rec.state == 'issued':
                raise UserError(_("Return the issued medicines before cancelling."))
            # The person who created it can cancel it (so can a dispenser).
            if rec.create_uid != self.env.user and not is_dispenser:
                raise UserError(_(
                    "Only the creator (%s) or a Pharmacy Dispenser can cancel "
                    "this requisition."
                ) % rec.create_uid.name)
            rec._charges().unlink()
            rec.charge_id = False
            rec.state = 'cancelled'
        return True

    def action_view_pickings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stock Transfers'),
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.picking_ids.ids)],
        }


class PharmacyRequisitionLine(models.Model):
    _name = 'pharmacy.requisition.line'
    _description = 'Pharmacy Requisition Line'

    requisition_id = fields.Many2one('pharmacy.requisition', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Medicine', required=True)
    requested_qty = fields.Float('Requested', default=1.0)
    issued_qty = fields.Float('Issued')
    returned_qty = fields.Float('Returned')
    issued_done_qty = fields.Float('Issued (processed)', readonly=True, copy=False)
    returned_done_qty = fields.Float('Returned (processed)', readonly=True, copy=False)
    unit_price = fields.Float('Unit Price')
    subtotal = fields.Float('Subtotal', compute='_compute_subtotal', store=True)

    @api.depends('issued_qty', 'returned_qty', 'unit_price')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = ((rec.issued_qty or 0.0) - (rec.returned_qty or 0.0)) * (rec.unit_price or 0.0)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            if rec.product_id:
                rec.unit_price = rec.product_id.lst_price
                if not rec.issued_qty:
                    rec.issued_qty = rec.requested_qty or 1.0
