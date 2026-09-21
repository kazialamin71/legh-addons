from odoo import fields, models


class HospitalAdmission(models.Model):
    """Commission accrual for an admitted patient.

    A counter bill accrues the moment it is confirmed, because that is when its
    money is final. An admission's is not: the ward charge ledger grows for as
    long as the patient stays, and the bed charge is recomputed from the length
    of stay every time ``_rebuild_charges`` runs. So the accrual happens once,
    at final settlement, off the finished ledger.

    That ledger is also the only place where the whole admission is visible in
    one shape -- bed, ICU, NICU, oxygen, medicine, doctor fees and the
    investigations pulled in from the patient's bills -- which is what lets one
    MOU say "40% of the NICU bed charge and 30% of the investigations" and have
    both halves come out of the same pass.
    """
    _name = 'hospital.admission'
    _inherit = ['hospital.admission', 'commission.referral.discount.mixin']

    def _referral_discount_referrer(self):
        self.ensure_one()
        return self.ref_doctors, self.referral

    def btn_final_settlement(self):
        res = super().btn_final_settlement()
        for rec in self.filtered(lambda r: r.state == 'released'):
            rec._accrue_commissions()
        return res

    def admission_cancel(self):
        res = super().admission_cancel()
        # Void only un-settled accruals; settled/paid ones stay for audit.
        # sudo: the ward user need not be a commission user.
        self.env['commission.line'].sudo().search([
            ('admission_id', 'in', self.ids), ('state', '=', 'accrued'),
        ]).write({'state': 'cancelled'})
        return res

    # -------------------------------------------------------------------------
    # ACCOMMODATION CONTEXT
    # -------------------------------------------------------------------------
    def _accommodation_intervals(self):
        """[(start, end_or_None, bed.category)] for the stay, earliest first.

        Lines with no start date or no bed are skipped: they occupy nothing and
        would otherwise swallow every charge under a blank category.
        """
        self.ensure_one()
        lines = self.hospital_bed_line_id.filtered(
            lambda l: l.start_date and l.bed_no and l.bed_no.category_id)
        return [(l.start_date, l.end_date, l.bed_no.category_id)
                for l in lines.sorted(lambda l: l.start_date)]

    def _accommodation_at(self, when, charge=None):
        """Where the patient was lying when ``when`` happened.

        Intervals are half-open -- start <= when < end -- so a charge dated at
        the exact moment of a transfer belongs to the accommodation the patient
        moved *into*. Closed on both sides, that charge would match two beds and
        the rate would depend on iteration order.

        Charges dated outside every interval still have to land somewhere, and
        the fallbacks are chosen so that silence is never the answer:

        * before the first bed was allocated -- the investigations taken during
          admission itself, billed while the patient is still at the counter --
          take the first accommodation. Anything else quietly pays an ICU
          admission's opening tests at the general-ward rate.
        * after the last bed line ended, or in a gap between two, take the
          nearest preceding accommodation: the one they had just left.
        """
        self.ensure_one()
        # A bed charge names its own bed line outright; no date arithmetic can
        # be more accurate than that, and a zero-length line has no interval to
        # be found in at all.
        if charge is not None and charge.source_model == 'hospital.bed.line':
            line = self.env['hospital.bed.line'].browse(charge.source_res_id).exists()
            if line and line.bed_no.category_id:
                return line.bed_no.category_id

        intervals = self._accommodation_intervals()
        if not intervals:
            return self.env['bed.category']
        if not when:
            return intervals[0][2]
        if when < intervals[0][0]:
            return intervals[0][2]
        for start, end, category in intervals:
            if start <= when and (not end or when < end):
                return category
        preceding = [i for i in intervals if i[0] <= when]
        return preceding[-1][2] if preceding else intervals[0][2]

    # -------------------------------------------------------------------------
    # COMMISSION ACCRUAL
    # -------------------------------------------------------------------------
    def _commission_header_discount(self):
        """The admission's own discount, spread over the charges by value.

        Same reasoning as on the bill: a discount granted on the admission as a
        whole never touches the individual charge rows, so an MOU set to follow
        what was collected has to be handed each charge's share of it.

        :returns: dict {charge id: discount borne by that charge}
        """
        self.ensure_one()
        charges = self.charge_ids
        total = sum(charges.mapped('total_amount'))
        # ``after_discount`` is what leih19 computes as the admission-level
        # giveaway; charge-level discounts are already inside total_amount.
        # Same as on the bill: the referral discount has its own charge-back
        # line, so it is kept out of the share spread across the charges.
        discount = (self.after_discount or 0.0) - (self.referral_discount or 0.0)
        if total <= 0 or discount <= 0:
            return {charge.id: 0.0 for charge in charges}
        discount = min(discount, total)
        return {charge.id: discount * (charge.total_amount or 0.0) / total
                for charge in charges}

    def _accrue_commissions(self):
        """Accrue commission per ward charge for each referrer with a rule.

        The referrers are the admission's own: the referring doctor and the
        broker in ``referral``. ``provider_id`` on a charge is the
        doctor who *did* the work, not the one who referred it, and is
        deliberately not treated as a referrer here.

        Idempotent per (charge, referrer), so re-settling a re-opened admission
        tops up the accrual rather than doubling it.
        """
        self.ensure_one()
        # sudo: accrual is system-driven; the settling user need not be a
        # commission user.
        CommissionLine = self.env['commission.line'].sudo()
        existing = CommissionLine.search([('admission_id', '=', self.id)])
        done_keys = {
            (l.admission_charge_id.id, l.doctor_id.id, l.broker_id.id) for l in existing
        }
        today = fields.Datetime.now()
        header_discount = self._commission_header_discount()
        self._accrue_referral_discount('admission_id', today)
        Bill = self.env['bill.register']

        doctor = self.ref_doctors
        broker = self.referral
        if not doctor and not broker:
            return True

        for charge in self.charge_ids:
            share = header_discount.get(charge.id, 0.0)
            accommodation = self._accommodation_at(charge.date, charge=charge)
            for doctor_rec, broker_rec in ((doctor, False), (False, broker)):
                if not doctor_rec and not broker_rec:
                    continue
                key = (charge.id,
                       doctor_rec.id if doctor_rec else False,
                       broker_rec.id if broker_rec else False)
                if key in done_keys:
                    continue
                config = Bill._find_commission_config(doctor_rec, broker_rec)
                if not config:
                    continue
                res = config.compute_commission(
                    entry=charge.item_id or None,
                    charge_item=charge.charge_item_id or None,
                    department=charge.unit_id or None,
                    service_type=charge.service_type,
                    accommodation=accommodation,
                    qty=charge.qty,
                    net_amount=charge.total_amount,
                    gross_amount=charge.gross_amount,
                    discount_amount=charge.discount,
                    header_discount=share,
                )
                if res['commission'] <= 0:
                    continue
                CommissionLine.create({
                    'admission_id': self.id,
                    'admission_charge_id': charge.id,
                    'doctor_id': doctor_rec.id if doctor_rec else False,
                    'broker_id': broker_rec.id if broker_rec else False,
                    'commission_configuration_id': config.id,
                    'department_id': charge.unit_id.id if charge.unit_id else False,
                    'name': charge.item_id.id if charge.item_id else False,
                    'charge_item_id': charge.charge_item_id.id if charge.charge_item_id else False,
                    'service_type': charge.service_type,
                    'accommodation_category_id': accommodation.id if accommodation else False,
                    'description': charge.description,
                    'test_amount': res['base'],
                    'discount_amount': (charge.discount or 0.0) + share,
                    'after_discount': (charge.total_amount or 0.0) - share,
                    'mou_payable_comm_var': res['rate'],
                    'mou_payable_comm_fixed': res['fixed'],
                    'mou_payable_comm_max_cap': res['cap'],
                    'payable_amount': res['commission'],
                    'accrual_date': today,
                    'state': 'accrued',
                })
                done_keys.add(key)
        return True
