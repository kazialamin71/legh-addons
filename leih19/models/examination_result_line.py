from odoo import api, fields, models


class ExaminationResultLine(models.Model):
    _name = 'examination.result.line'
    _description = 'Result Line (component value)'
    _order = 'sequence, id'

    result_id = fields.Many2one(
        'examination.result', string='Result', required=True, ondelete='cascade',
    )
    entry_line_id = fields.Many2one(
        'examination.entry.line', string='Component', required=True, ondelete='restrict',
    )

    # mirrored from the catalogue line so the form can render correctly
    name = fields.Char(related='entry_line_id.name', string='Name', readonly=True)
    sequence = fields.Integer(related='entry_line_id.sequence', store=True, readonly=True)
    result_type = fields.Selection(related='entry_line_id.result_type', readonly=True)
    uom = fields.Char(related='entry_line_id.uom', readonly=True)
    method_id = fields.Many2one(related='entry_line_id.method_id', string='Method', readonly=True)
    reference_value = fields.Char(related='entry_line_id.reference_value', readonly=True)
    reference_value_male = fields.Char(related='entry_line_id.reference_value_male', readonly=True)
    reference_value_female = fields.Char(related='entry_line_id.reference_value_female', readonly=True)
    reference_value_child = fields.Char(related='entry_line_id.reference_value_child', readonly=True)
    ref_low = fields.Float(related='entry_line_id.ref_low', readonly=True)
    ref_high = fields.Float(related='entry_line_id.ref_high', readonly=True)
    critical_low = fields.Float(related='entry_line_id.critical_low', readonly=True)
    critical_high = fields.Float(related='entry_line_id.critical_high', readonly=True)
    is_group_header = fields.Boolean(related='entry_line_id.is_group_header', readonly=True)
    print_style = fields.Selection(related='entry_line_id.print_style', readonly=True)
    decimals = fields.Integer(related='entry_line_id.decimals', readonly=True)
    panel_boxed = fields.Boolean(related='entry_line_id.panel_boxed', readonly=True)
    parent_line_id = fields.Many2one(related='entry_line_id.parent_line_id', readonly=True)
    show_when_value_id = fields.Many2one(related='entry_line_id.show_when_value_id', readonly=True)

    # captured values (only the one matching result_type is meaningful)
    value_numeric = fields.Float('Numeric Value')
    value_text = fields.Text('Text Value')
    value_selection_id = fields.Many2one(
        'examination.possible.value', string='Selection Value',
        domain="[('examination_line_id', '=', entry_line_id)]",
    )

    flag = fields.Selection(
        [('', 'Normal'),
         ('L', 'Low'),
         ('H', 'High'),
         ('LL', 'Critical Low'),
         ('HH', 'Critical High'),
         ('A', 'Abnormal')],
        compute='_compute_flag', store=True, default='',
    )

    is_visible = fields.Boolean(
        compute='_compute_is_visible', store=False,
        help='False if a parent line gates this component and its value does not match show_when_value.',
    )

    display_value = fields.Char(
        compute='_compute_display_value', string='Display Value',
        help='Result value formatted for printing (blank for unfilled numerics).',
    )
    has_value = fields.Boolean(compute='_compute_display_value')

    @api.depends('result_type', 'value_numeric', 'value_text', 'value_selection_id',
                 'is_group_header', 'decimals')
    def _compute_display_value(self):
        for rec in self:
            value = ''
            if not rec.is_group_header:
                if rec.result_type == 'numeric':
                    # blank for unfilled (zero) numerics; '%g' drops trailing .0
                    # unless the component asks for fixed decimals (2.00 pg/mL).
                    if not rec.value_numeric:
                        value = ''
                    elif rec.decimals:
                        value = '%.*f' % (rec.decimals, rec.value_numeric)
                    else:
                        value = '%g' % rec.value_numeric
                elif rec.result_type == 'selection':
                    value = rec.value_selection_id.name or ''
                else:
                    value = rec.value_text or ''
            rec.display_value = value
            rec.has_value = bool(value)

    @api.depends(
        'value_numeric', 'value_selection_id',
        'ref_low', 'ref_high', 'critical_low', 'critical_high',
        'result_type', 'entry_line_id',
    )
    def _compute_flag(self):
        for rec in self:
            flag = ''
            if rec.is_group_header:
                rec.flag = ''
                continue
            if rec.result_type == 'numeric':
                v = rec.value_numeric
                if rec.critical_low and v and v < rec.critical_low:
                    flag = 'LL'
                elif rec.critical_high and v and v > rec.critical_high:
                    flag = 'HH'
                elif rec.ref_low and v and v < rec.ref_low:
                    flag = 'L'
                elif rec.ref_high and v and v > rec.ref_high:
                    flag = 'H'
            elif rec.result_type == 'selection' and rec.value_selection_id:
                default = rec.entry_line_id.possible_value_ids.filtered(lambda x: x.is_default)
                if default and rec.value_selection_id not in default:
                    flag = 'A'
            rec.flag = flag

    @api.depends('result_id.result_line_ids.value_selection_id', 'parent_line_id', 'show_when_value_id')
    def _compute_is_visible(self):
        for rec in self:
            if not rec.parent_line_id:
                rec.is_visible = True
                continue
            parent_row = rec.result_id.result_line_ids.filtered(
                lambda r: r.entry_line_id == rec.parent_line_id
            )
            if not parent_row:
                rec.is_visible = True
            else:
                rec.is_visible = parent_row.value_selection_id == rec.show_when_value_id
