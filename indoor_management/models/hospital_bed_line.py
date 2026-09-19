from datetime import timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

DEFAULT_TZ = "Asia/Dhaka"


def _tz_of(env):
    name = env.user.tz or env.context.get("tz") or DEFAULT_TZ
    try:
        return pytz.timezone(name)
    except Exception:
        return pytz.timezone(DEFAULT_TZ)


def _to_local(dt_utc_naive, tz):
    return pytz.utc.localize(dt_utc_naive).astimezone(tz)


def _cycle_start_for(dt_local, start_hour, end_hour):
    """Local-time start of the billing cycle covering dt_local."""
    if dt_local.hour >= start_hour:
        return dt_local.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    if dt_local.hour < end_hour:
        prev = dt_local - timedelta(days=1)
        return prev.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    # Grace hour (end_hour..start_hour) — snap to today's cycle, so the minutes
    # a patient takes to actually leave after checkout time are not charged.
    return dt_local.replace(hour=start_hour, minute=0, second=0, microsecond=0)


def _cycle_end_for(cycle_start_local, end_hour):
    nxt = cycle_start_local + timedelta(days=1)
    return nxt.replace(hour=end_hour, minute=0, second=0, microsecond=0)


def _overlap_hours(line_s, line_e, cyc_s, cyc_e):
    s = max(line_s, cyc_s)
    e = min(line_e, cyc_e)
    if e <= s:
        return 0.0
    return (e - s).total_seconds() / 3600.0


class HospitalBedLine(models.Model):
    _inherit = "hospital.bed.line"

    ward_id = fields.Many2one(
        "hospital.ward", string="Ward",
        related="bed_no.ward_id", store=True, readonly=True,
    )
    category_id = fields.Many2one(
        "bed.category", string="Category",
        related="bed_no.category_id", store=True, readonly=True,
    )
    # Not stored: a bed's availability changes as other patients come and go,
    # and a stored copy would be a snapshot of whenever this line was last
    # written -- green long after somebody else moved in.
    bed_state = fields.Selection(
        related="bed_no.state", string="Bed Status", readonly=True,
    )
    days_count = fields.Float(
        string="Days",
        compute="_compute_charges", store=True,
        digits=(12, 2),
    )
    manual_override = fields.Boolean(
        string="Manual Charge",
        help="When checked, the Total Amount is kept as entered and not recomputed.",
    )
    shift_reason = fields.Char(string="Shift Reason")
    is_current = fields.Boolean(
        string="Currently Occupying",
        compute="_compute_is_current", store=True,
    )
    total_amount = fields.Float(
        string="Total Amount",
        compute="_compute_charges", store=True, readonly=False,
    )

    @api.depends("end_date")
    def _compute_is_current(self):
        for rec in self:
            rec.is_current = not rec.end_date

    @api.depends(
        "start_date", "end_date", "perday_charge", "bed_qty", "manual_override",
        "hospital_bed_item_id",
        "hospital_bed_item_id.hospital_bed_line_id.start_date",
        "hospital_bed_item_id.hospital_bed_line_id.end_date",
        "hospital_bed_item_id.hospital_bed_line_id.perday_charge",
        "hospital_bed_item_id.hospital_bed_line_id.bed_qty",
    )
    def _compute_charges(self):
        tz = _tz_of(self.env)
        now_utc = fields.Datetime.now()

        per_adm_results = {}
        admissions = self.mapped("hospital_bed_item_id")
        for adm in admissions:
            per_adm_results.update(self._calc_admission_days(adm.hospital_bed_line_id, tz, now_utc))

        for line in self:
            if not line.start_date or not line.bed_no:
                line.days_count = 0.0
                if not line.manual_override:
                    line.total_amount = 0.0
                continue
            if line.hospital_bed_item_id and line.id in per_adm_results:
                days = per_adm_results[line.id]
            else:
                days = self._calc_solo_days(line, tz, now_utc)
            line.days_count = days
            if not line.manual_override:
                line.total_amount = days * (line.perday_charge or 0.0) * (line.bed_qty or 1)

    def _charge_rule(self):
        """The charge rule billing this line, via its bed's category."""
        self.ensure_one()
        return self.env['bed.charge.rule']._for_category(self.bed_no.category_id)

    @api.model
    def _calc_solo_days(self, line, tz, now_utc):
        start_local = _to_local(line.start_date, tz)
        end_local = _to_local(line.end_date or now_utc, tz)
        if end_local <= start_local:
            return 0.0
        rule = line._charge_rule()
        start_hour, end_hour = rule._cycle_hours()
        days = 0.0
        cs = _cycle_start_for(start_local, start_hour, end_hour)
        while cs < end_local:
            ce = _cycle_end_for(cs, end_hour)
            days += rule.day_fraction(_overlap_hours(start_local, end_local, cs, ce))
            cs += timedelta(days=1)
        return days

    @api.model
    def _calc_admission_days(self, lines, tz, now_utc):
        """Per-line days_count for all bed lines under one admission, applying shift rule."""
        intervals = []  # (line, start_local, end_local)
        # Key every line, saved or not: a record being edited in the form carries
        # a NewId, and NewId is always falsy, so filtering on ``l.id`` dropped
        # exactly those lines and the accumulation below raised KeyError.
        result = {line.id: 0.0 for line in lines}
        for line in lines:
            if not line.start_date or not line.bed_no:
                continue
            s = _to_local(line.start_date, tz)
            e = _to_local(line.end_date or now_utc, tz)
            if e <= s:
                continue
            intervals.append((line, s, e))
        if not intervals:
            return result

        # The cycle grid belongs to the admission, not to one line, so it comes
        # from the rule of the accommodation the patient started in. Shifting
        # from a ward to ICU must not re-cut the day under the patient.
        Rule = self.env['bed.charge.rule']
        first_line = min(intervals, key=lambda i: i[1])[0]
        start_hour, end_hour = first_line._charge_rule()._cycle_hours()

        min_start = min(i[1] for i in intervals)
        max_end = max(i[2] for i in intervals)
        cs = _cycle_start_for(min_start, start_hour, end_hour)
        while cs < max_end:
            ce = _cycle_end_for(cs, end_hour)
            in_cycle = []
            for line, s, e in intervals:
                h = _overlap_hours(s, e, cs, ce)
                if h > 0:
                    in_cycle.append((line, h, s))
            if in_cycle:
                in_cycle.sort(key=lambda x: x[2])
                # Whoever the patient is lying in when the cycle closes carries
                # the day in full -- the bed was theirs for the night whatever
                # time they moved into it. Each accommodation vacated earlier in
                # the same cycle is charged by its own category's bands: two
                # hours in a ward before an ICU transfer is half a ward-day
                # under the standard rule, six is a whole one.
                for line, hours, _s in in_cycle[:-1]:
                    rule = Rule._for_category(line.bed_no.category_id)
                    result[line.id] += rule.day_fraction(hours)
                last_line, last_hours, _s = in_cycle[-1]
                if len(in_cycle) > 1:
                    result[last_line.id] += 1.0
                else:
                    rule = Rule._for_category(last_line.bed_no.category_id)
                    result[last_line.id] += rule.day_fraction(last_hours)
            cs += timedelta(days=1)
        return result

    @api.constrains("bed_no", "start_date", "end_date", "hospital_bed_item_id")
    def _check_bed_not_double_booked(self):
        """One patient per bed at a time.

        Enforced here rather than in the shift wizard because a bed can be
        allocated from three places -- the wizard, the admission's Bed tab, and
        code -- and only a constraint covers all of them. Overlap is compared on
        the dates, not just "is there an open line", so back-dating a stay onto a
        period the bed was already occupied is caught too. A missing end_date
        means "still in it", i.e. an open-ended interval.
        """
        for rec in self:
            if not rec.bed_no or not rec.start_date:
                continue
            if rec.hospital_bed_item_id.state == "cancelled":
                continue
            domain = [
                ("id", "!=", rec.id),
                ("bed_no", "=", rec.bed_no.id),
                ("start_date", "!=", False),
                ("hospital_bed_item_id.state", "!=", "cancelled"),
            ]
            # other.start < this.end  (no end = runs forever, so no upper bound)
            if rec.end_date:
                domain.append(("start_date", "<", rec.end_date))
            # ...and this.start < other.end
            clash = self.search(domain).filtered(
                lambda o: (not o.end_date or o.end_date > rec.start_date)
                # A stay closed before it began occupies nothing. These appear
                # when an admission is cancelled while its bed line is still
                # future-dated; without this they would block the bed for good.
                and not (o.end_date and o.start_date and o.end_date <= o.start_date))
            if clash:
                other = clash[0]
                raise ValidationError(_(
                    "Bed %(bed)s is already allocated to %(patient)s "
                    "(admission %(adm)s) from %(start)s.\n\n"
                    "Release or shift that patient first, or choose another bed.",
                    bed=rec.bed_no.display_name,
                    patient=other.hospital_bed_item_id.patient_name.name or "-",
                    adm=other.hospital_bed_item_id.name or "-",
                    start=other.start_date,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Final compute pass: during create, the field-assignment order can cause
        # the initial compute to see start_date=False (when manual_override is set
        # before start_date in cache). Re-run once after all fields are populated.
        records._compute_charges()
        records.mapped("bed_no")._sync_state()
        return records

    def write(self, vals):
        # Beds touched before the write matter as much as the ones touched after:
        # moving a line to a different bed has to free the one it left.
        before = self.mapped("bed_no")
        res = super().write(vals)
        (before | self.mapped("bed_no"))._sync_state()
        return res

    def unlink(self):
        beds = self.mapped("bed_no")
        res = super().unlink()
        beds._sync_state()
        return res

    @api.onchange("bed_no")
    def _onchange_bed_indoor(self):
        for rec in self:
            if rec.bed_no:
                rec.perday_charge = rec.bed_no.get_effective_charge()
                if not rec.start_date:
                    rec.start_date = fields.Datetime.now()
                if not rec.bed_qty:
                    rec.bed_qty = 1
