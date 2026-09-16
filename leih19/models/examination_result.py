import base64

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ExaminationResult(models.Model):
    _name = 'examination.result'
    _description = 'Examination Result (per patient/test)'
    _order = 'reported_at desc, id desc'
    _rec_name = 'name'

    name = fields.Char('Result No.', readonly=True, copy=False, default='New')
    state = fields.Selection(
        [('draft', 'Draft'),
         ('in_progress', 'In Progress'),
         ('verified', 'Verified'),
         ('released', 'Released'),
         ('cancelled', 'Cancelled')],
        default='draft', required=True, copy=False,
    )

    patient_id = fields.Many2one('patient.info', string='Patient', required=True)
    patient_sex = fields.Selection(related='patient_id.sex', string='Sex', readonly=True)
    patient_age = fields.Char(related='patient_id.age', string='Age', readonly=True)

    entry_id = fields.Many2one(
        'examination.entry', string='Test', required=True,
        help='Catalogue entry; defines components, antibiotic panel, and defaults.',
    )
    category = fields.Selection(related='entry_id.category', store=True, readonly=True)
    report_layout = fields.Selection(related='entry_id.report_layout', string='Report Layout', store=True, readonly=True)
    department_id = fields.Many2one(related='entry_id.department', string='Department', store=True, readonly=True)

    doctor_id = fields.Many2one('doctors.profile', string='Requesting Doctor')
    reported_by_id = fields.Many2one('doctors.profile', string='Reported By')

    sticker_id = fields.Many2one(
        'diagnosis.sticker', string='Lab Order / Sticker',
        help='Optional link back to the legacy sample collection record.',
    )
    specimen_id = fields.Many2one(
        'lab.specimen', string='Specimen', ondelete='set null',
        help='Physical sample tube. Multiple results may share a specimen when their tests use the same tube color and department.',
    )
    bill_register_id = fields.Many2one(
        'bill.register', string='Bill', ondelete='set null',
        help='Bill this lab result belongs to (set when auto-generated from bill confirmation).',
    )

    sample_state = fields.Selection(
        [('no_sample', 'No Sample Needed'),
         ('awaiting', 'Awaiting Collection'),
         ('collected', 'Collected'),
         ('received', 'Received in Lab'),
         ('processed', 'Sample Processed'),
         ('cancelled', 'Sample Cancelled')],
        string='Sample Status', compute='_compute_sample_state', store=True,
        help='Where the physical sample is. Tests that need no tube (radiology, '
             'descriptive) are always "No Sample Needed".')
    sample_collected = fields.Boolean(
        'Sample Collected', compute='_compute_sample_state', store=True,
        help='The tube for this test has been collected from the patient.')
    sample_received = fields.Boolean(
        'Sample in Lab', compute='_compute_sample_state', store=True,
        help='The tube for this test has been received in the lab - results can be entered.')

    sample_collected_at = fields.Datetime('Sample Collected At')
    reported_at = fields.Datetime('Reported At', default=fields.Datetime.now)
    verified_at = fields.Datetime('Verified At', readonly=True)
    verified_by_id = fields.Many2one('res.users', string='Verified By', readonly=True)

    method_id = fields.Many2one('lab.method', string='Method')
    instrument_id = fields.Many2one('lab.instrument', string='Instrument')

    # Microbiology actuals (overridable defaults from entry_id)
    incubation_hours = fields.Integer('Incubation (hours)')
    incubation_temp_c = fields.Float('Incubation Temp (°C)')
    culture_medium = fields.Char('Culture Medium')
    organism_identified = fields.Char('Organism Identified')
    show_antibiogram = fields.Boolean(
        'Show Antibiogram on Report', default=True,
        help='Untick to hide the antibiogram (sensitivity panel) on the printed report.')

    # --- Transfusion / Cross matching (report_layout == 'transfusion') ---
    donor_name = fields.Char('Donor Name')
    donor_age = fields.Char('Donor Age')
    donor_sex = fields.Char('Donor Sex')
    patient_blood_group = fields.Char("Patient's Blood Group (ABO/Rh)")
    donor_blood_group = fields.Char("Donor's Blood Group (ABO/Rh)")
    donation_type = fields.Char('Type of Donation')
    blood_component = fields.Char('Type of Blood Component')
    cross_match_status = fields.Char('Cross Match Status (RT & 37°C ICT)')
    bag_no = fields.Char('Bag No.')
    transfusion_note = fields.Text('Transfusion Note')

    result_line_ids = fields.One2many(
        'examination.result.line', 'result_id', string='Result Lines', copy=True,
    )
    antibiogram_line_ids = fields.One2many(
        'examination.result.antibiogram.line', 'result_id', string='Antibiogram', copy=True,
    )

    clinical_note = fields.Text('Clinical Note / Interpretation')

    referred_institute = fields.Char(
        'Institute Name',
        help='Referring institute printed in the report header (blank for '
             'walk-in / self-referred patients).')

    report_block_ids = fields.One2many(
        'lab.report.block', 'result_id', string='Report Notes', copy=True,
        help='Text blocks printed under the result table. Seeded from the '
             'catalogue test; edit freely for this patient.')
    print_disclaimer = fields.Boolean(
        'Print Disclaimer', default=True,
        help='Print the department (or company) disclaimer at the bottom of this report.')


    # --- Descriptive / Radiology narrative ---
    template_id = fields.Many2one(
        'examination.report.template', string='Template',
        help='Pre-defined narrative template to load into the body.',
    )
    available_template_ids = fields.Many2many(
        'examination.report.template', compute='_compute_available_template_ids',
    )
    narrative_html = fields.Html('Narrative / Findings', sanitize=False)

    has_antibiogram = fields.Boolean(compute='_compute_has_antibiogram')

    patient_history_count = fields.Integer(
        'Previous Tests', compute='_compute_patient_history_count',
        help='Other lab tests recorded for this patient (cancelled ones excluded).')

    @api.depends('patient_id')
    def _compute_patient_history_count(self):
        """Count the patient's other lab tests, so the lab user can open the
        test history straight from the report they are typing."""
        history = self.filtered('patient_id')
        (self - history).patient_history_count = 0
        if not history:
            return
        counts = {}
        if history.patient_id:
            groups = self._read_group(
                [('patient_id', 'in', history.patient_id.ids),
                 ('state', '!=', 'cancelled')],
                groupby=['patient_id'], aggregates=['__count'],
            )
            counts = {patient.id: count for patient, count in groups}
        for rec in history:
            count = counts.get(rec.patient_id.id, 0)
            # The record being edited is itself in that count - don't show it.
            if rec._origin.id and rec.state != 'cancelled':
                count -= 1
            rec.patient_history_count = max(count, 0)

    @api.depends('entry_id.report_template_ids')
    def _compute_available_template_ids(self):
        for rec in self:
            rec.available_template_ids = rec.entry_id.report_template_ids

    @api.depends('category', 'antibiogram_line_ids')
    def _compute_has_antibiogram(self):
        for rec in self:
            rec.has_antibiogram = rec.category == 'microbiology' and bool(rec.antibiogram_line_ids)

    @api.depends('specimen_id', 'specimen_id.state')
    def _compute_sample_state(self):
        mapping = {'draft': 'awaiting', 'collected': 'collected',
                   'received': 'received', 'processed': 'processed',
                   'cancelled': 'cancelled'}
        for rec in self:
            if not rec.specimen_id:
                rec.sample_state = 'no_sample'
            else:
                rec.sample_state = mapping.get(rec.specimen_id.state, 'awaiting')
            rec.sample_collected = rec.sample_state in ('collected', 'received', 'processed')
            rec.sample_received = rec.sample_state in ('received', 'processed')

    @api.onchange('entry_id')
    def _onchange_entry_id(self):
        for rec in self:
            if not rec.entry_id:
                continue
            rec.method_id = rec.entry_id.default_method_id
            rec.instrument_id = rec.entry_id.default_instrument_id
            rec.reported_by_id = rec.entry_id.reported_by_id
            rec.print_disclaimer = rec.entry_id.print_disclaimer
            if not rec.report_block_ids:
                rec.report_block_ids = rec.entry_id.report_block_ids._copy_to_result_vals()
            if rec.entry_id.category == 'microbiology':
                rec.incubation_hours = rec.entry_id.default_incubation_hours
                rec.incubation_temp_c = rec.entry_id.default_incubation_temp_c
                rec.culture_medium = rec.entry_id.default_culture_medium

    @api.onchange('template_id')
    def _onchange_template_id(self):
        for rec in self:
            if rec.template_id and not rec.narrative_html:
                rec.narrative_html = rec.template_id.body_html

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('examination.result') or 'New'
            entry = self.env['examination.entry'].browse(vals.get('entry_id')) if vals.get('entry_id') else False
            if entry:
                vals.setdefault('method_id', entry.default_method_id.id if entry.default_method_id else False)
                vals.setdefault('instrument_id', entry.default_instrument_id.id if entry.default_instrument_id else False)
                vals.setdefault('reported_by_id', entry.reported_by_id.id if entry.reported_by_id else False)
                vals.setdefault('print_disclaimer', entry.print_disclaimer)
                if not vals.get('report_block_ids') and entry.report_block_ids:
                    vals['report_block_ids'] = entry.report_block_ids._copy_to_result_vals()
                if entry.category == 'microbiology':
                    vals.setdefault('incubation_hours', entry.default_incubation_hours)
                    vals.setdefault('incubation_temp_c', entry.default_incubation_temp_c)
                    vals.setdefault('culture_medium', entry.default_culture_medium)
                if not vals.get('result_line_ids'):
                    vals['result_line_ids'] = [
                        (0, 0, {
                            'entry_line_id': line.id,
                            'value_text': line.default_value if line.result_type == 'text' else False,
                            'value_selection_id': self._default_selection_value(line),
                        })
                        for line in entry.examination_entry_line.sorted('sequence')
                    ]
                if entry.category == 'microbiology' and not vals.get('antibiogram_line_ids'):
                    vals['antibiogram_line_ids'] = [
                        (0, 0, {'antibiotic_id': ab.id})
                        for ab in entry.antibiotic_ids.sorted('sequence')
                    ]
                if entry.category in ('descriptive', 'radiology') and not vals.get('narrative_html') and entry.report_template_ids:
                    first_template = entry.report_template_ids[0]
                    vals.setdefault('template_id', first_template.id)
                    vals['narrative_html'] = first_template.body_html or ''
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        # A tube is done when every test on it is done - and re-opens if one of
        # them is sent back for re-entry.
        if 'state' in vals or 'specimen_id' in vals:
            self.specimen_id._sync_state_from_results()
        return res

    def _report_page_groups(self):
        """Group results into printed pages. Results that share the same
        department and tube color print on ONE page; a test flagged
        'Individual' on its catalogue entry always prints on its own page."""
        groups = []          # ordered list of keys
        by_key = {}          # key -> recordset
        for res in self:
            entry = res.entry_id
            if entry.individual:
                key = ('solo', res.id)
            else:
                key = (res.department_id.id, entry.tube_color_id.id)
            if key not in by_key:
                by_key[key] = self.browse()
                groups.append(key)
            by_key[key] |= res
        return [by_key[k] for k in groups]

    def _report_two_columns(self):
        """Split visible result lines into two balanced columns for the
        clinical-pathology layout. Splits at the midpoint by line count so the
        two columns stay even, but never ends the left column on a group header
        (which would orphan it). Returns (left_lines, right_lines)."""
        self.ensure_one()
        lines = self.result_line_ids.filtered(
            lambda l: l.is_visible and (l.is_group_header or l.name or l.has_value)
        ).sorted('sequence')
        n = len(lines)
        half = (n + 1) // 2
        if 0 < half < n and lines[half - 1].is_group_header:
            half -= 1
        return lines[:half], lines[half:]

    def _report_panels(self):
        """Group visible lines into printable panels for the Special layout.

        Each group header opens a panel and everything under it belongs to that
        panel until the next header; components entered before any header land
        in one unlabelled panel, which is what a form with no groups at all
        prints as. Within a panel the components are bucketed by their print
        style, so the template lays out each kind without walking the list
        itself.

        The buckets print in a fixed order - rows, then the band, then the
        verdict - because that is the order every one of these slips reads in:
        what was measured, then the readings, then the call. Sequence still
        orders the components inside each bucket, so interleaving a band
        component between two rows is the one arrangement this cannot express.
        """
        self.ensure_one()
        panels = []
        current = None

        def open_panel(header=None):
            return {
                'header': header,
                'boxed': bool(header and header.panel_boxed),
                'rows': [],
                'band': [],
                'verdicts': [],
            }

        lines = self.result_line_ids.filtered(
            lambda l: l.is_visible and (l.is_group_header or l.name or l.has_value)
        ).sorted('sequence')
        for line in lines:
            if line.is_group_header:
                if current:
                    panels.append(current)
                current = open_panel(line)
                continue
            if current is None:
                current = open_panel()
            if line.print_style == 'band':
                current['band'].append(line)
            elif line.print_style == 'verdict':
                current['verdicts'].append(line)
            else:
                current['rows'].append(line)
        if current:
            panels.append(current)
        return panels

    # ------------------------------------------------------------------
    # Printing helpers - keep formatting out of the QWeb template so every
    # layout renders the house style the same way.
    # ------------------------------------------------------------------
    def _report_dt(self, value, fmt='%d/%m/%Y %H:%M'):
        """Datetime in the user's timezone, house format (17/06/2026 16:38)."""
        if not value:
            return ''
        return fields.Datetime.context_timestamp(self, value).strftime(fmt)

    def _report_barcode_uri(self, width=600, height=100):
        """Specimen (or bill) barcode inlined as a data: URI.

        A `/report/barcode/...` src makes wkhtmltopdf take an HTTP round trip
        back into Odoo; this server hosts several databases with no db_filter,
        so that unauthenticated request cannot resolve one and answers 404 -
        which prints as a silent empty box. Rendering the PNG here removes the
        round trip. See patient.info._id_card_barcode_uri for the same fix.
        """
        self.ensure_one()
        value = self.specimen_id.name or self.bill_register_id.name or self.name
        if not value:
            return ''
        png = self.env['ir.actions.report'].barcode(
            'Code128', value, width=width, height=height, humanreadable=False)
        return 'data:image/png;base64,%s' % base64.b64encode(png).decode()

    def _report_now(self, fmt='%d/%m/%Y %H:%M'):
        """Print timestamp in the user's timezone."""
        return self._report_dt(fields.Datetime.now(), fmt)

    def _report_title(self):
        """Centred report title, e.g. 'Laboratory Report : Serology'."""
        self.ensure_one()
        section = self.department_id.name or self.entry_id.name or ''
        return 'Laboratory Report : %s' % section if section else 'Laboratory Report'

    def _report_age_gender(self):
        self.ensure_one()
        sex = dict(self.patient_id._fields['sex'].selection).get(self.patient_sex) or ''
        parts = [p for p in (self.patient_age or '', sex.upper()) if p]
        return '/'.join(parts) or '-'

    def _report_patient_name(self):
        """Patient name with the hospital ID, as the house format prints it."""
        self.ensure_one()
        name = self.patient_id.name or '-'
        return '%s (ID-%s)' % (name, self.patient_id.patient_id) if self.patient_id.patient_id else name

    def _report_patient_ref(self):
        """Bottom-of-page identity line: 'Mr SADAF (ID-34085)/LAB/2026/00157'."""
        self.ensure_one()
        return '%s/%s' % (self._report_patient_name(), self.name or '')

    def _report_line_method(self, line):
        """Method printed on one component row: the component's own method,
        else the method of the result."""
        self.ensure_one()
        return line.method_id.name or self.method_id.name or ''

    def _report_disclaimer_html(self):
        """Department disclaimer, else the company-wide one; empty when the
        test is set not to print one."""
        self.ensure_one()
        if not self.print_disclaimer:
            return ''
        return self.department_id.report_disclaimer_html or self.env.company.lab_report_disclaimer_html or ''

    def _report_page_disclaimer(self):
        """Disclaimer for a page of results - printed once, from the first test
        on the page that asks for one."""
        for result in self:
            html = result._report_disclaimer_html()
            if html:
                return html
        return ''

    def _default_selection_value(self, entry_line):
        if entry_line.result_type != 'selection':
            return False
        default = entry_line.possible_value_ids.filtered(lambda v: v.is_default)
        return default[:1].id if default else False

    # --- workflow buttons ---
    # Sample states that mean the tube is not in the lab yet, so no result may
    # be typed against it. Tube-less tests ('no_sample') are never blocked.
    _BLOCKING_SAMPLE_STATES = ('awaiting', 'collected', 'cancelled')

    def action_start(self):
        for rec in self:
            if rec.sample_state in rec._BLOCKING_SAMPLE_STATES:
                label = dict(rec._fields['sample_state'].selection)[rec.sample_state]
                raise UserError(_(
                    'Specimen %(specimen)s for %(test)s is "%(status)s". Receive the '
                    'tube in the lab before entering results.',
                    specimen=rec.specimen_id.name or '-',
                    test=rec.entry_id.name or rec.name,
                    status=label))
        self.write({'state': 'in_progress'})

    def action_verify(self):
        self.write({
            'state': 'verified',
            'verified_at': fields.Datetime.now(),
            'verified_by_id': self.env.user.id,
        })

    def action_release(self):
        self.write({'state': 'released'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        """Send a cancelled or released report back for re-entry. The old
        verification stamp no longer applies to what will be typed next."""
        self.write({
            'state': 'draft',
            'verified_at': False,
            'verified_by_id': False,
        })

    def action_print_report(self):
        """Print just this result."""
        self.ensure_one()
        return self.env.ref('leih19.action_report_examination_result').report_action(self)

    def action_print_bill_reports(self):
        """Print all the bill's tests merged; warns if any are not verified."""
        self.ensure_one()
        if not self.bill_register_id:
            return self.action_print_report()
        return self.bill_register_id._print_lab_reports_checked()

    def action_view_patient_history(self):
        """All other tests of this patient, newest first."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Test History - %s', self.patient_id.name or ''),
            'res_model': 'examination.result',
            'view_mode': 'list,form',
            'domain': [('patient_id', '=', self.patient_id.id),
                       ('id', '!=', self._origin.id),
                       ('state', '!=', 'cancelled')],
            'context': {'default_patient_id': self.patient_id.id},
        }
