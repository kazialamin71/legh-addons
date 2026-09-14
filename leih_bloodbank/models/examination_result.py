"""Transfusion data on the lab result.

Cross matching is an investigation like any other: it is billed on
bill.register, which raises the ``examination.result``, the technologist enters
it, it is verified and printed. What makes it different is only the *shape* of
what gets entered and printed -- a donor, two blood groups, a bag, and a
screening panel whose answers decide whether the unit may leave the bank.

So nothing here reinvents the investigation workflow. It replaces the free-text
transfusion fields leih19 declared with controlled ones, links the donor to the
donor register, and works out the two things the printed slip has to say that
no lab report has to: which results are compatibility and which are screening,
and whether the unit is fit to issue.
"""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .blood_groups import (BLOOD_COMPONENTS, BLOOD_GROUPS, CROSS_MATCH_STATUS,
                           DONATION_TYPES, SEXES, UNSAFE_TOKENS)


class ExaminationResult(models.Model):
    _inherit = 'examination.result'

    is_transfusion = fields.Boolean(compute='_compute_is_transfusion', store=True)

    donor_id = fields.Many2one(
        'blood.donar', string='Donor (Register)', ondelete='restrict',
        help='Pick the donor from the register and their name, age, sex and '
             'group fill in. Leave blank and type the donor block by hand for a '
             'walk-in whose registration has not been done yet.')

    # Same field names leih19 declared -- the form, the report and any existing
    # integration keep working; only the vocabulary is now fixed.
    donor_sex = fields.Selection(SEXES, string='Donor Sex')
    patient_blood_group = fields.Selection(
        BLOOD_GROUPS, string="Patient's Blood Group (ABO/Rh)")
    donor_blood_group = fields.Selection(
        BLOOD_GROUPS, string="Donor's Blood Group (ABO/Rh)")
    donation_type = fields.Selection(DONATION_TYPES, string='Type of Donation')
    blood_component = fields.Selection(BLOOD_COMPONENTS, string='Type of Blood Component')
    cross_match_status = fields.Selection(
        CROSS_MATCH_STATUS, string='Cross Match Status (RT & 37°C ICT)')

    group_mismatch = fields.Boolean(
        'ABO/Rh Mismatch', compute='_compute_transfusion_verdict', store=True,
        help='Donor and patient groups are not identical. Not always an error -- '
             'O negative is issued to anyone in an emergency -- but it is always '
             'worth a second look before the unit leaves the bank.')
    fit_for_issue = fields.Boolean(
        'Fit for Issue', compute='_compute_transfusion_verdict', store=True,
        help='Every mandatory screening test non-reactive and both cross match '
             'phases compatible.')
    unfit_reason = fields.Char(
        'Not Fit Because', compute='_compute_transfusion_verdict', store=True)

    @api.depends('report_layout')
    def _compute_is_transfusion(self):
        for rec in self:
            rec.is_transfusion = rec.report_layout == 'transfusion'

    # ------------------------------------------------------------------ donor
    @api.onchange('donor_id')
    def _onchange_donor_id(self):
        for rec in self:
            donor = rec.donor_id
            if not donor:
                continue
            rec.donor_name = donor.doner_name or donor.name
            rec.donor_age = donor.age or rec.donor_age
            rec.donor_sex = donor.sex or rec.donor_sex
            # The group on file is a convenience, not the answer: the bag is
            # regrouped at crossmatch and the technologist confirms it here.
            rec.donor_blood_group = donor.blood_group or rec.donor_blood_group

    # ------------------------------------------------------------- the verdict
    @api.model
    def _value_is_unsafe(self, line):
        """True when a result line reads as reactive, positive or incompatible.

        Two independent tests, because a catalogue built by the hospital cannot
        be assumed to word its options the way this one does: the printed value
        against a vocabulary of unsafe words, and the printed value against the
        catalogue's own reference value. Either firing is enough.
        """
        value = (line.display_value or '').strip()
        if not value:
            return False
        lowered = value.lower()
        if any(token in lowered for token in UNSAFE_TOKENS):
            return True
        reference = (line.reference_value or '').strip()
        return bool(reference) and lowered != reference.lower()

    @api.depends('result_line_ids.value_selection_id', 'result_line_ids.value_text',
                 'result_line_ids.value_numeric', 'report_layout',
                 'donor_blood_group', 'patient_blood_group')
    def _compute_transfusion_verdict(self):
        for rec in self:
            rec.group_mismatch = bool(
                rec.is_transfusion and rec.donor_blood_group and rec.patient_blood_group
                and rec.donor_blood_group != rec.patient_blood_group)
            if not rec.is_transfusion:
                rec.fit_for_issue = False
                rec.unfit_reason = False
                continue
            unsafe, unanswered = [], []
            for line in rec.result_line_ids:
                if line.is_group_header or line.result_type == 'text':
                    continue
                if not line.has_value:
                    unanswered.append(line.name or '/')
                elif rec._value_is_unsafe(line):
                    unsafe.append('%s: %s' % (line.name or '/', line.display_value))
            if unsafe:
                rec.fit_for_issue = False
                rec.unfit_reason = ', '.join(unsafe)
            elif unanswered:
                # Not a failure, but not a pass either. A blank screening test is
                # the one thing that must never read as "fit to issue".
                rec.fit_for_issue = False
                rec.unfit_reason = _('Not yet answered: %s') % ', '.join(unanswered)
            else:
                rec.fit_for_issue = True
                rec.unfit_reason = False

    # ------------------------------------------------------------------- bag
    @api.constrains('bag_no', 'state')
    def _check_bag_no_unique(self):
        """One bag, one crossmatch.

        Issuing the same unit against two patients is the error a blood bank
        exists to prevent, and it is invisible on either slip on its own.
        """
        for rec in self:
            bag = (rec.bag_no or '').strip()
            if not bag or rec.state == 'cancelled':
                continue
            clash = self.search([
                ('id', '!=', rec.id),
                ('bag_no', '=ilike', bag),
                ('state', '!=', 'cancelled'),
            ], limit=1)
            if clash:
                raise ValidationError(_(
                    'Bag %(bag)s is already cross matched on %(other)s for '
                    'patient %(patient)s. A unit can only be issued once -- '
                    'check the bag number, or cancel that crossmatch if it was '
                    'entered in error.',
                    bag=bag, other=clash.name or '/',
                    patient=clash.patient_id.name or '/'))

    # ------------------------------------------------------------- the report
    def _transfusion_sections(self):
        """Result lines split into the sections the catalogue itself declares.

        The components of a crossmatch item arrive as one flat list with group
        headers in it -- COMPATIBILITY TESTING, then MANDATORY DONOR SCREENING --
        and the old template printed the lot, headers and all, under a single
        "Donor Screening Tests" heading. So the slip listed the cross match
        phases as though they were screening tests and printed the standing
        instruction note as if it were a result.

        Reading the headers back out keeps the printed sections exactly as
        whoever built the catalogue item arranged them, with no list of section
        names hard-coded here: add a "VIRAL MARKERS -- NAT" header to the item
        and it prints as its own section.

        Free-text components are pulled out as notes rather than rows, which is
        what they are.
        """
        self.ensure_one()
        sections, current = [], None

        def _open(title):
            section = {'title': title, 'lines': [], 'notes': []}
            sections.append(section)
            return section

        for line in self.result_line_ids.sorted(lambda l: (l.sequence, l.id)):
            if not line.is_visible:
                continue
            if line.is_group_header:
                current = _open(line.name or '')
                continue
            if current is None:
                current = _open('')
            if line.result_type == 'text' and not line.is_group_header:
                if line.display_value:
                    current['notes'].append(line.display_value)
                continue
            if line.name or line.has_value:
                current['lines'].append(line)

        return [s for s in sections if s['lines'] or s['notes']]
