from odoo import fields, models


class BillRegister(models.Model):
    """Commission accrual hooks layered onto the base bill.register."""
    _inherit = 'bill.register'

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

    def _accrue_commissions(self):
        """Accrue commission per billed item for EACH referrer that has a rule:
        the doctor (line doctor, else bill referring doctor) and the broker can
        both earn on the same bill. Idempotent per (bill line, referrer)."""
        self.ensure_one()
        # sudo: accrual is system-driven; the confirming user need not be a
        # commission user.
        CommissionLine = self.env['commission.line'].sudo()
        existing = CommissionLine.search([('bill_id', '=', self.id)])
        done_keys = {
            (l.bill_line_id.id, l.doctor_id.id, l.broker_id.id) for l in existing
        }
        today = self.date or fields.Datetime.now()

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
                    line.name, line.product_qty, line.total_amount,
                    line.gross_amount, line.total_discount,
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
                    'test_amount': res['base'],
                    'discount_amount': line.total_discount,
                    'after_discount': line.total_amount,
                    'mou_payable_comm_var': res['rate'],
                    'mou_payable_comm_fixed': res['fixed'],
                    'mou_payable_comm_max_cap': res['cap'],
                    'payable_amount': res['commission'],
                    'accrual_date': today,
                    'state': 'accrued',
                })
                done_keys.add(key)
        return True
