from odoo import models, fields


class ExaminationEntryLine(models.Model):
    _name = 'examination.entry.line'
    _description = 'Examination Entry Line'
    _order = 'examinationentry_id, sequence, id'

    name = fields.Char('Name', ondelete='cascade')
    examinationentry_id = fields.Many2one('examination.entry', string='Test Entry')
    reference_value = fields.Char('Reference Value')
    bold = fields.Boolean('Bold')
    group_by = fields.Boolean('Group By')
    others = fields.Char('Others')

    # --- Component configuration (Phase 1) ---
    sequence = fields.Integer('Sequence', default=10)
    uom = fields.Char('Unit')
    method_id = fields.Many2one(
        'lab.method', string='Method',
        help='Method printed on this component\'s row (ELISA, Photometry, '
             'Calculation...). Falls back to the method of the result itself.')
    result_type = fields.Selection(
        [('numeric', 'Numeric'),
         ('text', 'Free Text'),
         ('selection', 'Selection')],
        string='Result Type', default='numeric',
        help='"Selection" makes the technician pick from Possible Values (e.g. Positive / Negative).',
    )
    reference_value_male = fields.Char('Ref. Value (Male)')
    reference_value_female = fields.Char('Ref. Value (Female)')
    reference_value_child = fields.Char('Ref. Value (Child)')
    possible_value_ids = fields.One2many(
        'examination.possible.value', 'examination_line_id', string='Possible Values',
    )
    is_group_header = fields.Boolean(
        'Group Header',
        help='Tick to render this line as a bold section header instead of an editable component.',
    )

    # --- Printed shape of the component (Special Form layout) ---
    # Three primitives cover the bespoke assay slips - a bordered panel, a row
    # of readings side by side, and one emphasised verdict - so a new form of
    # that kind is catalogue configuration rather than another QWeb template.
    print_style = fields.Selection(
        [('row', 'Label / Value Row'),
         ('band', 'Side by Side in a Band'),
         ('verdict', 'Boxed Verdict')],
        string='Print Style', default='row', required=True,
        help='How this component prints on a Special Form report.\n'
             '- Label / Value Row: the usual label left, value right.\n'
             '- Side by Side in a Band: shares one horizontal band with the '
             'other Band components of its group, label above value (the three '
             'tube readings of a QuantiFERON assay).\n'
             '- Boxed Verdict: the line the clinician acts on, printed large in '
             'its own box (Final Result: POSITIVE).',
    )
    panel_boxed = fields.Boolean(
        'Draw Panel Border',
        help='On a Group Header: draw a border around that header and every '
             'component under it, the way the house QuantiFERON slip boxes its '
             'assay panel.',
    )

    # --- Conditional rendering between lines (e.g. show Antibiogram only if Growth) ---
    parent_line_id = fields.Many2one(
        'examination.entry.line', string='Depends On Line', ondelete='set null',
        domain="[('examinationentry_id', '=', examinationentry_id), ('id', '!=', id)]",
        help='If set, this line is shown at result time only when the parent line equals "Show When Value".',
    )
    show_when_value_id = fields.Many2one(
        'examination.possible.value', string='Show When Value',
        domain="[('examination_line_id', '=', parent_line_id)]",
        help='Trigger value on the parent line that makes this line visible.',
    )
    default_value = fields.Char(
        'Default Value',
        help='Prefilled value at result entry (e.g. "No growth shown after 48h incubation at 37°C").',
    )

    # --- Numeric reference range + critical thresholds for auto-flagging ---
    decimals = fields.Integer(
        'Printed Decimals',
        help='Fixed decimal places for a numeric result on the printed report: '
             '2 prints a nil tube reading of 2 as "2.00", the way the assay '
             'reports it. Leave at 0 to print the value as entered, trailing '
             'zeros dropped.')

    ref_low = fields.Float('Normal Range Low')
    ref_high = fields.Float('Normal Range High')
    critical_low = fields.Float('Critical Low')
    critical_high = fields.Float('Critical High')
