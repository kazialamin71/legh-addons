from odoo import models, fields

class OpticsDailyCollection(models.Model):
    _name = 'optics.daily.collection'
    _description = 'OpticsDailyCollection'

    date_start = fields.Datetime('Date', required=True)
    date_end = fields.Datetime('Date End', required=True)

    def _collection_sales(self):
        """Optics sales that fall inside the selected window (non-cancelled)."""
        self.ensure_one()
        domain = [('state', '!=', 'cancelled')]
        if self.date_start:
            domain.append(('date', '>=', self.date_start))
        if self.date_end:
            domain.append(('date', '<=', self.date_end))
        return self.env['optics.sale'].search(domain, order='date')

    def _collection_totals(self):
        """Grand total / paid / due summed across the window's sales."""
        sales = self._collection_sales()
        return {
            'grand_total': sum(sales.mapped('grand_total')),
            'paid': sum(sales.mapped('paid')),
            'due': sum(sales.mapped('due')),
            'count': len(sales),
        }
