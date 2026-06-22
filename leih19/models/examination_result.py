from odoo import api, fields, models


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

    @api.depends('entry_id.report_template_ids')
    def _compute_available_template_ids(self):
        for rec in self:
            rec.available_template_ids = rec.entry_id.report_template_ids

    @api.depends('category', 'antibiogram_line_ids')
    def _compute_has_antibiogram(self):
        for rec in self:
            rec.has_antibiogram = rec.category == 'microbiology' and bool(rec.antibiogram_line_ids)

    @api.onchange('entry_id')
    def _onchange_entry_id(self):
        for rec in self:
            if not rec.entry_id:
                continue
            rec.method_id = rec.entry_id.default_method_id
            rec.instrument_id = rec.entry_id.default_instrument_id
            rec.reported_by_id = rec.entry_id.reported_by_id
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

    def _default_selection_value(self, entry_line):
        if entry_line.result_type != 'selection':
            return False
        default = entry_line.possible_value_ids.filtered(lambda v: v.is_default)
        return default[:1].id if default else False

    # --- workflow buttons ---
    def action_start(self):
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
        self.write({'state': 'draft'})

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
