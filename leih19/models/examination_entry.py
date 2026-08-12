from odoo import api, models, fields


class ExaminationEntry(models.Model):
    _name = 'examination.entry'
    _description = 'Examination Entry'

    name = fields.Char('Item Name', required=True)
    department = fields.Many2one('diagnosis.department', string='Department')
    rate = fields.Integer('Rate')
    base_rate = fields.Integer('Base Rate')
    required_time = fields.Integer('Required time(Days)')
    sample_req = fields.Boolean('Sample Required')
    individual = fields.Boolean('Individual')
    manual = fields.Boolean('Manual')
    merge = fields.Boolean('Merge')
    dependency = fields.Boolean('Dependency')
    lab_not_required = fields.Boolean('No Lab Required')
    indoor = fields.Boolean('Indoor Item')
    sample_type = fields.Many2one('sample.type', string='Sample Type')
    accounts_id = fields.Many2one('account.account', string='Account ID')
    examination_entry_line = fields.One2many('examination.entry.line', 'examinationentry_id')
    merge_ids = fields.Many2many('examination.merge.line', 'merge_item_rel', string='Merge')
    support_item_ids = fields.One2many(
        'examination.support.item', 'entry_id', string='Supporting Items',
        help='Items automatically added to the bill whenever this item is billed '
             '(e.g. disposable bed sheet, test tube).')

    # --- Reporting / workflow configuration (Phase 1) ---
    service_group = fields.Selection(
        [('diagnostic', 'Diagnostic / Lab'),
         ('physiotherapy', 'Physiotherapy'),
         ('dental', 'Dental'),
         ('consultation', 'Consultation'),
         ('procedure', 'Procedure'),
         ('oxygen', 'Oxygen'),
         ('consumable', 'Consumable'),
         ('other', 'Other Service')],
        string='Service Group', default='diagnostic', required=True,
        help='Classifies the item. Only "Diagnostic / Lab" items generate lab '
             'results / specimens; the rest are pure service charges.',
    )
    category = fields.Selection(
        [('pathology', 'Pathology'),
         ('microbiology', 'Microbiology'),
         ('radiology', 'Radiology'),
         ('descriptive', 'Descriptive (USG/Echo)')],
        string='Test Category', default='pathology',
        help='Drives the data shape of the result (numeric components, antibiogram, narrative).',
    )
    report_type = fields.Selection(
        [('pathology', 'Pathology'),
         ('radiology', 'Radiology'),
         ('descriptive', 'Descriptive (USG/Echo)'),
         ('other', 'Other')],
        string='Report Type', default='pathology',
        help='Drives how the printed report is laid out.',
    )
    report_layout = fields.Selection(
        [('tabular', 'Standard Tabular (grouped)'),
         ('two_column', 'Two-Column Clinical Pathology'),
         ('microbiology', 'Microbiology (Culture & Sensitivity)'),
         ('narrative', 'Narrative / Descriptive'),
         ('transfusion', 'Transfusion / Cross Matching'),
         ('special', 'Special Form (Mantoux / HLA-B27)')],
        string='Report Layout',
        compute='_compute_report_layout', store=True, readonly=False,
        help='Controls how the printed lab report body is laid out for this test.\n'
             '- Tabular: Test / Result / Unit / Reference (Biochemistry, Haematology, Serology, AMH, HCG, Troponin).\n'
             '- Two-Column: clinical pathology routines (Urine R/M/E, Stool R/E).\n'
             '- Microbiology: organism + antibiogram.\n'
             '- Narrative: free rich-text findings (Cytopathology, Histopathology, USG).\n'
             '- Transfusion: donor block, blood groups, screening (Cross Matching).\n'
             '- Special: label/value form for tests like Mantoux or HLA-B27.',
    )

    @api.depends('category')
    def _compute_report_layout(self):
        """Seed a sensible layout from the test category, but never overwrite a
        layout already chosen manually (so existing records get a good default
        on upgrade while staying overridable per test)."""
        mapping = {
            'microbiology': 'microbiology',
            'radiology': 'narrative',
            'descriptive': 'narrative',
            'pathology': 'tabular',
        }
        for rec in self:
            if not rec.report_layout:
                rec.report_layout = mapping.get(rec.category, 'tabular')
    tube_color_id = fields.Many2one(
        'tube.color', string='Tube Color',
        help='Used to group items on the same sticker at sample collection.',
    )
    needs_separate_tube = fields.Boolean(
        'Requires Own Tube',
        help='Tick if this test always needs its own specimen tube even when other tests share the same tube color and department.',
    )
    reported_by_id = fields.Many2one(
        'doctors.profile', string='Reported By (Specialist)',
        help='Pathologist / radiologist whose name prints as "Reported By".',
    )
    default_method_id = fields.Many2one(
        'lab.method', string='Default Method',
        help='Routine method for this test; tech can override on individual results.',
    )
    default_instrument_id = fields.Many2one(
        'lab.instrument', string='Default Instrument',
        help='Routine analyzer for this test; tech can override on individual results.',
    )
    report_template_ids = fields.Many2many(
        'examination.report.template', 'examination_entry_template_rel',
        'examination_entry_id', 'template_id',
        string='Report Templates',
        help='Pre-defined narrative templates available to the technician (radiology / USG / Echo).',
    )

    # --- Microbiology-specific catalogue fields ---
    default_incubation_hours = fields.Integer('Default Incubation (hours)')
    default_incubation_temp_c = fields.Float('Default Incubation Temp (°C)')
    default_culture_medium = fields.Char('Default Culture Medium')
    antibiotic_ids = fields.Many2many(
        'lab.antibiotic', 'examination_entry_antibiotic_rel',
        'entry_id', 'antibiotic_id',
        string='Antibiotic Panel',
        help='Panel of antibiotics the technician will fill at result time when growth is reported.',
    )
