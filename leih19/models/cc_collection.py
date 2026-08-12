from odoo import models, fields

class CcCollection(models.Model):
    _name = 'cc.collection'
    _description = 'CcCollection'

    date_start = fields.Datetime('Date Start', required=True)
    date_end = fields.Datetime('Date End', required=True)

    def _receipts(self):
        """Confirmed money receipts collected inside the selected window.

        ``leih.money.receipt.date`` is a Date field, so the datetime bounds are
        reduced to their date parts before searching."""
        self.ensure_one()
        domain = [('state', '=', 'confirm')]
        if self.date_start:
            domain.append(('date', '>=', fields.Date.to_date(self.date_start)))
        if self.date_end:
            domain.append(('date', '<=', fields.Date.to_date(self.date_end)))
        return self.env['leih.money.receipt'].search(domain, order='date')

    def _cc_summary(self):
        """Collection grouped by the source document type, with counts and amounts."""
        receipts = self._receipts()
        buckets = [
            ('bill_id', 'Diagnostic / Bill'),
            ('admission_id', 'Admission'),
            ('general_admission_id', 'General Admission'),
            ('optics_sale_id', 'Optics'),
        ]
        rows = []
        for fname, label in buckets:
            recs = receipts.filtered(lambda m: m[fname])
            if recs:
                rows.append({
                    'label': label,
                    'count': len(recs),
                    'amount': sum(recs.mapped('amount')),
                })
        # receipts not attached to any of the known sources
        other = receipts.filtered(
            lambda m: not (m.bill_id or m.admission_id
                           or m.general_admission_id or m.optics_sale_id))
        if other:
            rows.append({
                'label': 'Other',
                'count': len(other),
                'amount': sum(other.mapped('amount')),
            })
        return rows

    def _cc_total(self):
        return sum(self._receipts().mapped('amount'))
