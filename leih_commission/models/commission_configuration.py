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
    deduct_from_discount = fields.Boolean(
        'Deduct Excess Discount From Commission',
        help="Discount given beyond 'Overall Discount Rate' is taken off the "
             "commission. Leave off when the referrer's price is fixed and any "
             "further discount is the hospital's own giveaway.")
    commission_base = fields.Selection(
        [('line_net', "Item Net (ignore bill-level discount)"),
         ('bill_net', "Collected Net (bill-level discount included)")],
        string='Commission Base', default='line_net', required=True,
        help="Which amount the commission is worked out on.\n\n"
             "Item Net: the item's own price after its own discount. The "
             "referrer's negotiated price is what counts; a further discount "
             "given by management does not cut their commission.\n\n"
             "Collected Net: the item's share of the bill's grand total, so "
             "every discount -- including one entered on the bill header -- "
             "reduces the commission with it.")
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

    # -------------------------------------------------------------------------
    # RULE MATCHING
    # -------------------------------------------------------------------------
    def _match_line(self, entry=None, charge_item=None, department=None,
                    service_type=None, accommodation=None):
        """The scoped rule covering this item, most specific first.

        A named test or charge item beats the department it sits in, which in
        turn beats the service bucket. Without that order a blanket "30% on
        diagnostics" would swallow the one test that was negotiated separately.

        Accommodation is checked before any of that: a rule written for ICU and
        NICU is consulted in full before one that names no accommodation, so
        "40% on investigations in ICU" wins over "10% on investigations" for a
        patient in ICU and loses to it everywhere else. A rule naming
        accommodations is simply not consulted for a charge raised outside them.
        """
        self.ensure_one()
        lines = self.commission_configuration_line_ids
        scoped = lines.browse()
        if accommodation:
            scoped = lines.filtered(
                lambda l: l.accommodation_category_ids
                and accommodation in l.accommodation_category_ids)
        unscoped = lines.filtered(lambda l: not l.accommodation_category_ids)
        for pool in (scoped, unscoped):
            for predicate in (
                lambda l: entry and l.test_id and l.test_id == entry,
                lambda l: charge_item and l.charge_item_id and l.charge_item_id == charge_item,
                lambda l: department and l.department_id and l.department_id == department,
                lambda l: service_type and l.service_type and l.service_type == service_type,
            ):
                match = pool.filtered(predicate)[:1]
                if match:
                    return match
        return lines.browse()

    # -------------------------------------------------------------------------
    # COMPUTATION
    # -------------------------------------------------------------------------
    def compute_commission(self, entry=None, qty=1.0, net_amount=0.0, gross_amount=0.0,
                           discount_amount=0.0, header_discount=0.0,
                           charge_item=None, department=None, service_type=None,
                           base_rate=None, accommodation=None):
        """Commission payable for one billed item under this rule.

        Shared by bill.register and hospital.admission accrual, which is why the
        item is described by parts rather than passed as a record: a NICU bed
        charge has no ``examination.entry`` behind it, only a service bucket and
        a price.

        :param entry: examination.entry, when the item is a diagnostic test
        :param charge_item: admission.charge.item, for a ward/admission charge
        :param department: diagnosis.department the income belongs to
        :param service_type: hospital.admission.charge bucket ('nicu', 'bed'...)
        :param accommodation: bed.category the patient was in when the charge
            was raised, which is what separates an ICU investigation rate from
            a general-ward one
        :param qty: quantity billed
        :param net_amount: item amount after its own discount
        :param gross_amount: list price x qty, before any discount
        :param discount_amount: discount given on the item itself
        :param header_discount: this item's share of a bill-level discount --
            money the hospital gave away after the referrer's price was agreed
        :param base_rate: unit floor price, when the caller knows it better than
            the catalogue does
        :returns: dict(base, rate, fixed, cap, commission)
        """
        self.ensure_one()
        qty = qty or 0.0
        net_amount = net_amount or 0.0
        header_discount = header_discount or 0.0
        if department is None:
            department = entry.department if entry else False
        if base_rate is None:
            base_rate = (entry.base_rate if entry else 0.0) or 0.0

        match = self._match_line(entry=entry, charge_item=charge_item,
                                 department=department, service_type=service_type,
                                 accommodation=accommodation)

        # A non-applicable line excludes the item from commission entirely.
        if match and not match.applicable:
            return {'base': 0.0, 'rate': 0.0, 'fixed': 0.0, 'cap': 0.0, 'commission': 0.0}

        # Under 'line_net' the bill-level discount never reaches the referrer:
        # their price was agreed before management chose to give more away.
        # Under 'bill_net' it does, so commission tracks what was collected.
        if self.commission_base == 'bill_net':
            chargeable = max(0.0, net_amount - header_discount)
            unreflected_discount = 0.0
        else:
            chargeable = net_amount
            unreflected_discount = header_discount

        # The excess-discount claw-back may only look at money the commission
        # base has not already given up. ``chargeable`` is net of the item's own
        # discount, so counting that discount again would charge the referrer
        # twice for it -- and on a margin rule it would charge them for the very
        # discount that defines their price: negotiate 7000 down to 4500, earn
        # 1000 over a 3500 floor, then lose it all to a 2500 'excess'.
        excess_discount = unreflected_discount

        cap = match.max_commission_amount if match else 0.0
        method = match.line_method if match else 'percentage'

        # Margin: the referrer keeps whatever the price exceeds the agreed floor.
        if method == 'margin':
            unit_base = (match.base_price or base_rate) or 0.0
            base_total = unit_base * qty
            commission = max(0.0, chargeable - base_total)
            commission = self._apply_excess_discount(commission, gross_amount, excess_discount)
            if cap:
                commission = min(commission, cap)
            return {'base': base_total, 'rate': 0.0, 'fixed': 0.0, 'cap': cap,
                    'commission': commission}

        # Percentage / fixed, from the matching line or the overall MOU rate.
        # Commission on the base rate is blind to every discount, so there the
        # claw-back is the only thing that makes a discount cost the referrer
        # anything and it has to see all of it.
        # 'Calculation on Base Price' is an MOU-wide switch, but a base rate is
        # a catalogue figure and plenty of billable things have none: a NICU bed
        # charge, oxygen, a doctor's visit fee. Applying the switch to those
        # would compute the commission on nothing and pay zero -- a rule that
        # looks configured, reports no error and quietly never pays. Where there
        # is no base rate to work on, the amount billed is the base.
        if self.calculation_base_price and base_rate:
            base = base_rate * qty
            excess = (discount_amount or 0.0) + header_discount
        else:
            base = chargeable
            excess = excess_discount
        rate = (match.variance_amount if match else self.overall_commission_rate) or 0.0
        fixed = (match.fixed_amount if match else 0.0) or 0.0
        commission = base * rate / 100.0 + fixed
        commission = self._apply_excess_discount(commission, gross_amount, excess)
        if cap:
            commission = min(commission, cap)
        return {'base': base, 'rate': rate, 'fixed': fixed, 'cap': cap,
                'commission': commission}

    def _apply_excess_discount(self, commission, gross_amount, discount_amount):
        """Subtract discount given beyond the MOU's allowed default discount.

        An allowance of 0% is a real setting -- "any discount comes out of the
        commission" -- so the switch alone decides whether this runs. Guarding
        on a non-zero allowance, as this once did, turned the strictest MOU into
        the most lenient one.
        """
        self.ensure_one()
        if not self.deduct_from_discount:
            return commission if commission > 0.0 else 0.0
        allowed = (gross_amount or 0.0) * (self.overall_default_discount or 0.0) / 100.0
        excess = (discount_amount or 0.0) - allowed
        if excess > 0:
            commission -= excess
        return commission if commission > 0.0 else 0.0
