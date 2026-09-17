from odoo import _, api, fields, models


class HospitalAdmission(models.Model):
    """Pharmacy side of an admission: what went out, what came back, what is billed.

    A ward draws medicine over many requisitions and hands a boxful back at
    discharge, so the two halves are counted separately and the bill takes the
    difference. ``medicine_adjusted_total`` is the figure the patient pays, and
    it is what the medicine charges on the ledger add up to.
    """
    _inherit = 'hospital.admission'

    pharmacy_requisition_ids = fields.One2many(
        'pharmacy.requisition', 'admission_id', string='Pharmacy Requisitions')
    pharmacy_requisition_count = fields.Integer(compute='_compute_pharmacy_req_count')

    # The same records split by document type, so the form can show one list of
    # issues and one of returns without the user filtering by hand.
    pharmacy_issue_ids = fields.One2many(
        'pharmacy.requisition', 'admission_id', string='Medicine Issued',
        domain=[('doc_type', '=', 'issue')])
    pharmacy_return_ids = fields.One2many(
        'pharmacy.requisition', 'admission_id', string='Medicine Returned',
        domain=[('doc_type', '=', 'return')])

    medicine_issued_total = fields.Float(
        'Medicine Issued', compute='_compute_medicine_totals', store=True,
        help='Value of every medicine issued to this admission.')
    medicine_returned_total = fields.Float(
        'Medicine Returned', compute='_compute_medicine_totals', store=True,
        help='Value of every medicine taken back into pharmacy stock.')
    medicine_adjusted_total = fields.Float(
        'Medicine Adjusted (billed)', compute='_compute_medicine_totals', store=True,
        help='Issued less returned - the medicine income billed on this admission.')

    @api.depends('pharmacy_requisition_ids.net_amount',
                 'pharmacy_requisition_ids.state',
                 'pharmacy_requisition_ids.doc_type')
    def _compute_medicine_totals(self):
        for rec in self:
            issued = returned = 0.0
            for req in rec.pharmacy_requisition_ids:
                if req.state not in ('issued', 'returned'):
                    continue
                # net_amount is signed: an issue adds, a return subtracts.
                if req.doc_type == 'return':
                    returned += -(req.net_amount or 0.0)
                else:
                    issued += req.net_amount or 0.0
            rec.medicine_issued_total = issued
            rec.medicine_returned_total = returned
            rec.medicine_adjusted_total = issued - returned

    def _compute_pharmacy_req_count(self):
        for rec in self:
            rec.pharmacy_requisition_count = len(rec.pharmacy_requisition_ids)

    # ------------------------------------------------------------------ returns
    def _pharmacy_processed_lines(self, doc_type):
        """Lines of this admission's processed documents of one type.

        Only processed quantities count. A draft requisition is a request, not a
        dispense, and crediting a return against it would let medicine be handed
        back before it was ever handed out.
        """
        self.ensure_one()
        return self.env['pharmacy.requisition.line'].search([
            ('requisition_id.admission_id', '=', self.id),
            ('requisition_id.doc_type', '=', doc_type),
            ('requisition_id.state', 'in', ('issued', 'returned')),
        ])

    def _pharmacy_returnable_qty(self, product, exclude_document=None, exclude_line=None):
        """How much of ``product`` this admission may still hand back.

        Everything issued across every requisition, less everything already
        returned. ``exclude_document`` / ``exclude_line`` leave the return being
        edited out of the "already returned" side, so re-validating a document
        does not count it against itself.
        """
        self.ensure_one()
        if not product:
            return 0.0
        issued = sum(
            line.issued_done_qty or 0.0
            for line in self._pharmacy_processed_lines('issue')
            if line.product_id == product
        )
        returned = sum(
            line.returned_done_qty or 0.0
            for line in self._pharmacy_processed_lines('return')
            if line.product_id == product
            and line.requisition_id != exclude_document
            and line != exclude_line
        )
        return max(issued - returned, 0.0)

    def _pharmacy_issue_price(self, product):
        """The price this admission was last charged for ``product``.

        A return credits what the patient was billed. Falling back to the list
        price would refund whatever the price list says today, which is not the
        same number once a price has been revised mid-stay.
        """
        self.ensure_one()
        lines = self._pharmacy_processed_lines('issue').filtered(
            lambda l: l.product_id == product and l.unit_price)
        if lines:
            return lines.sorted(lambda l: l.id)[-1].unit_price
        return product.lst_price if product else 0.0

    # ------------------------------------------------------------------ billing
    def action_calculate_payable(self):
        """Re-evaluate the pharmacy charges along with everything else.

        ``_rebuild_charges`` deliberately leaves charges owned by other modules
        alone, so the pharmacy has to refresh its own. Prices and quantities can
        be corrected on a document after it was processed, and Calculate Payable
        is where the bill is expected to catch up with all of it.
        """
        res = super().action_calculate_payable()
        for rec in self:
            for req in rec.pharmacy_requisition_ids:
                if req.state in ('issued', 'returned'):
                    req._sync_charge()
        return res

    # ------------------------------------------------------------------ actions
    def action_new_pharmacy_requisition(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pharmacy Requisition'),
            'res_model': 'pharmacy.requisition',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_admission_id': self.id, 'default_doc_type': 'issue'},
        }

    def action_new_pharmacy_return(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Medicine Return'),
            'res_model': 'pharmacy.requisition',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_admission_id': self.id,
                'default_doc_type': 'return',
            },
            'views': [(self.env.ref('leih_pharmacy.pharmacy_return_form_view').id, 'form')],
        }

    def action_view_pharmacy_requisitions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pharmacy Requisitions'),
            'res_model': 'pharmacy.requisition',
            'view_mode': 'list,form',
            'domain': [('admission_id', '=', self.id)],
            'context': {'default_admission_id': self.id},
        }

    def _medicine_statement_rows(self):
        """Every medicine movement on this admission, issued and returned apart.

        Read off the document lines rather than the charge ledger: the ledger
        holds one rolled-up amount per document (per income account), which is
        the right shape for a bill and useless for "which medicine, how many, at
        what rate".
        """
        self.ensure_one()
        issued, returned = [], []
        documents = self.pharmacy_requisition_ids.filtered(
            lambda r: r.state in ('issued', 'returned')
        ).sorted(lambda r: (r.date or fields.Datetime.now(), r.id))

        for doc in documents:
            is_return = doc.doc_type == 'return'
            bucket = returned if is_return else issued
            for line in doc.line_ids:
                qty = (line.returned_done_qty if is_return else line.issued_done_qty) or 0.0
                if not qty:
                    continue
                price = line.unit_price or 0.0
                bucket.append({
                    'date': fields.Datetime.context_timestamp(
                        self, doc.date).strftime('%d-%b-%Y') if doc.date else '',
                    'doc': doc.name or '',
                    'medicine': line.product_id.display_name or '',
                    'qty': qty,
                    'price': price,
                    'amount': qty * price,
                })
        return {'issued': issued, 'returned': returned}

    def action_print_medicine_statement(self):
        """Every medicine issued and returned on this admission, with the total."""
        self.ensure_one()
        return self.env.ref(
            'leih_pharmacy.action_report_admission_medicine').report_action(self)
