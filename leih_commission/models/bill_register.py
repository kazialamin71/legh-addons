from odoo import fields, models


class BillRegister(models.Model):
    """Commission accrual hooks layered onto the base bill."""
    _name = 'bill.register'
    _inherit = ['bill.register', 'commission.referral.discount.mixin']

    def _referral_discount_referrer(self):
        self.ensure_one()
        return self.ref_doctors, self.referral

    def bill_confirm(self):
        res = super().bill_confirm()
        self._accrue_commissions()
        return res

    def bill_cancel(self):
        res = super().bill_cancel()
        # Void only un-settled accruals; settled/paid ones stay for audit.
        # sudo: the billing user need not be a commission user.
        self.env['commission.line'].sudo().search([
            ('bill_id', '=', self.id), ('state', '=', 'accrued'),
        ]).write({'state': 'cancelled'})
        return res

    # -------------------------------------------------------------------------
    # COMMISSION ACCRUAL
    # -------------------------------------------------------------------------
    def _find_commission_config(self, doctor, broker):
        """Active commission rule for a doctor (preferred) or broker.
        Confirmed rules win; cancelled ones are never used."""
        Config = self.env['commission.configuration'].sudo()
        if doctor:
            base = [('doctor_id', '=', doctor.id)]
        elif broker:
            base = [('broker_id', '=', broker.id)]
        else:
            return Config.browse()
        config = Config.search(base + [('state', '=', 'done')], limit=1)
        if not config:
            config = Config.search(base + [('state', '!=', 'cancelled')], limit=1)
        return config

    def _commission_header_discount(self):
        """Bill-level discount, spread over the lines in proportion to value.

        The doctor/goodwill discounts are entered on the bill, not on the items,
        so an item's ``total_amount`` is blind to them: a bill of 7000 discounted
        30% still shows a 7000 line while the patient pays 4900. An MOU that
        wants commission to follow the money has to be told what that line's
        share of the giveaway was.

        :returns: dict {bill line id: discount borne by that line}
        """
        self.ensure_one()
        lines = self.bill_register_line_id
        line_total = sum(lines.mapped('total_amount'))
        # The referral discount is deducted in full on its own charge-back line,
        # so spreading it across the items as well would take it twice.
        discount = (line_total - (self.grand_total or 0.0)
                    - (self.referral_discount or 0.0))
        if line_total <= 0 or discount <= 0:
            return {line.id: 0.0 for line in lines}
        return {line.id: discount * (line.total_amount or 0.0) / line_total
                for line in lines}

    def _accrue_commissions(self):
        """Accrue commission per billed item for EACH referrer that has a rule:
        the doctor (line doctor, else bill referring doctor) and the broker can
        both earn on the same bill. Idempotent per (bill line, referrer)."""
        self.ensure_one()
        # An investigation raised against an admission is billed twice over:
        # once here and once on the admission's charge ledger, which
        # ``_rebuild_charges`` pulls these very lines into. Accruing on both
        # would pay the referrer twice for one test, so the admission -- which
        # sees the ward charges as well -- owns the whole admission's accrual.
        if self.general_admission_id:
            return True
        # sudo: accrual is system-driven; the confirming user need not be a
        # commission user.
        CommissionLine = self.env['commission.line'].sudo()
        existing = CommissionLine.search([('bill_id', '=', self.id)])
        done_keys = {
            (l.bill_line_id.id, l.doctor_id.id, l.broker_id.id) for l in existing
        }
        today = self.date or fields.Datetime.now()
        header_discount = self._commission_header_discount()
        self._accrue_referral_discount('bill_id', today)

        for line in self.bill_register_line_id:
            if not line.name:
                continue
            doctor = line.assign_doctors or self.ref_doctors
            broker = self.referral
            # one accrual per referrer present
            for doctor_rec, broker_rec in ((doctor, False), (False, broker)):
                if not doctor_rec and not broker_rec:
                    continue
                key = (line.id,
                       doctor_rec.id if doctor_rec else False,
                       broker_rec.id if broker_rec else False)
                if key in done_keys:
                    continue
                config = self._find_commission_config(doctor_rec, broker_rec)
                if not config:
                    continue
                res = config.compute_commission(
                    entry=line.name,
                    qty=line.product_qty,
                    net_amount=line.total_amount,
                    gross_amount=line.gross_amount,
                    discount_amount=line.total_discount,
                    header_discount=header_discount.get(line.id, 0.0),
                    department=line.department_id or (line.name.department if line.name else False),
                    service_type='diagnostic',
                )
                if res['commission'] <= 0:
                    continue
                CommissionLine.create({
                    'bill_id': self.id,
                    'bill_line_id': line.id,
                    'doctor_id': doctor_rec.id if doctor_rec else False,
                    'broker_id': broker_rec.id if broker_rec else False,
                    'commission_configuration_id': config.id,
                    'department_id': line.department_id.id if line.department_id else False,
                    'name': line.name.id,
                    'service_type': 'diagnostic',
                    'test_amount': res['base'],
                    'discount_amount': (line.total_discount or 0.0) + header_discount.get(line.id, 0.0),
                    'after_discount': (line.total_amount or 0.0) - header_discount.get(line.id, 0.0),
                    'mou_payable_comm_var': res['rate'],
                    'mou_payable_comm_fixed': res['fixed'],
                    'mou_payable_comm_max_cap': res['cap'],
                    'payable_amount': res['commission'],
                    'accrual_date': today,
                    'state': 'accrued',
                })
                done_keys.add(key)
        return True
