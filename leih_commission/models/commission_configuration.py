from odoo import fields, models


class CommissionConfiguration(models.Model):
    _name = 'commission.configuration'
    _description = 'CommissionConfiguration'

    name = fields.Char('Name')
    doctor_id = fields.Many2one('doctors.profile', string='Doctor/SR Name')
    broker_id = fields.Many2one('brokers.info', string='Broker Name')
    start_date = fields.Date('MOU Start Date')
    end_date = fields.Date('MOU End Date')
    overall_commission_rate = fields.Float('Overall Commission Rate (%)')
    overall_default_discount = fields.Float('Overall Discount Rate (%)')
    max_default_discount = fields.Float('Max Discount Rate (%)')
    deduct_from_discount = fields.Boolean('Deduct Excess Discount From Commission')
    add_few_departments = fields.Boolean('Add by Department')
    calculation_base_price = fields.Boolean('Calculation on Base Price')
    department_ids = fields.Many2one('diagnosis.department', string='Department List')
    commission_configuration_line_ids = fields.One2many('commission.configuration.line', 'commission_configuration_line_ids')
    state = fields.Selection([('pending', 'Pending'), ('done', 'Confirmed'), ('cancelled', 'Cancelled')], 'Status', default='pending', readonly=True)

    def action_confirm(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_to_pending(self):
        self.write({'state': 'pending'})

    def compute_commission(self, entry, qty, net_amount, gross_amount, discount_amount):
        """Compute the commission payable for one billed item under this rule.

        Shared by bill.register and hospital.admission accrual.

        :param entry: examination.entry (the test/item)
        :param qty: quantity billed
        :param net_amount: line amount after all discounts
        :param gross_amount: list price x qty (before discount)
        :param discount_amount: total discount given on the line
        :returns: dict(base, rate, fixed, cap, commission)
        """
        self.ensure_one()
        dept = entry.department if entry else False
        qty = qty or 0.0

        # Matching per-scope line: per-test wins over per-department. A matching
        # line overrides the overall rule with its own method.
        lines = self.commission_configuration_line_ids
        match = lines.filtered(lambda l: l.test_id and l.test_id == entry)[:1]
        if not match and dept:
            match = lines.filtered(lambda l: l.department_id and l.department_id == dept)[:1]

        if match:
            # Non-applicable line excludes the item from commission entirely.
            if not match.applicable:
                return {'base': 0.0, 'rate': 0.0, 'fixed': 0.0, 'cap': 0.0, 'commission': 0.0}

            cap = match.max_commission_amount or 0.0

            # Department/test margin: keep whatever the bill exceeds the base price.
            if match.line_method == 'margin':
                unit_base = (match.base_price or (entry.base_rate if entry else 0.0)) or 0.0
                base_total = unit_base * qty
                commission = max(0.0, (net_amount or 0.0) - base_total)
                if cap:
                    commission = min(commission, cap)
                return {'base': base_total, 'rate': 0.0, 'fixed': 0.0, 'cap': cap, 'commission': commission}

            # Department/test percentage override.
            base = ((entry.base_rate or 0.0) * qty) if (self.calculation_base_price and entry) else (net_amount or 0.0)
            rate = match.variance_amount or 0.0
            fixed = match.fixed_amount or 0.0
            commission = base * rate / 100.0 + fixed
            if cap:
                commission = min(commission, cap)
            commission = self._apply_excess_discount(commission, gross_amount, discount_amount)
            return {'base': base, 'rate': rate, 'fixed': fixed, 'cap': cap, 'commission': commission}

        # No matching line -> overall percentage.
        base = ((entry.base_rate or 0.0) * qty) if (self.calculation_base_price and entry) else (net_amount or 0.0)
        rate = self.overall_commission_rate or 0.0
        commission = base * rate / 100.0
        commission = self._apply_excess_discount(commission, gross_amount, discount_amount)
        return {'base': base, 'rate': rate, 'fixed': 0.0, 'cap': 0.0, 'commission': commission}

    def _apply_excess_discount(self, commission, gross_amount, discount_amount):
        """Subtract discount given beyond the MOU's allowed default discount."""
        self.ensure_one()
        if self.deduct_from_discount and self.overall_default_discount:
            allowed = (gross_amount or 0.0) * self.overall_default_discount / 100.0
            excess = (discount_amount or 0.0) - allowed
            if excess > 0:
                commission -= excess
        return commission if commission > 0.0 else 0.0
