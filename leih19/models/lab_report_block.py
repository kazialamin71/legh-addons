from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class LabReportBlock(models.Model):
    """A free text/HTML block printed under the result table.

    One model serves both ends: blocks hung on a catalogue entry are the
    per-test defaults, and they are copied onto every result created from that
    test so the technician can edit them for that one patient. Anything the
    reference reports show below the table - Precautionary Comments, a long
    Interpretation Result, Note, Comment, even an interpretation matrix table -
    is just a block, so a new kind of report never needs template code.
    """
    _name = 'lab.report.block'
    _description = 'Lab Report Text Block'
    _order = 'sequence, id'

    name = fields.Char(
        'Label', help='Printed as the block label, e.g. "Interpretation Result" '
                      'or "Note". Leave empty for an unlabelled paragraph.')
    sequence = fields.Integer(default=10)
    body_html = fields.Html(
        'Body', sanitize=False,
        help='Free content: paragraphs, lists, or a whole table (an '
             'interpretation matrix, for instance).')
    style = fields.Selection(
        [('stacked', 'Label above body'),
         ('inline', 'Label beside body (boxed)'),
         ('plain', 'Body only')],
        default='stacked', required=True,
        help='How the block prints. "Label beside body" reproduces the boxed '
             'Note: / Comment: rows of the house format.')

    entry_id = fields.Many2one(
        'examination.entry', string='Test', ondelete='cascade', index=True,
        help='Catalogue entry this block is a default for.')
    result_id = fields.Many2one(
        'examination.result', string='Result', ondelete='cascade', index=True,
        help='Result this block prints on.')

    @api.constrains('entry_id', 'result_id')
    def _check_single_parent(self):
        for rec in self:
            if bool(rec.entry_id) == bool(rec.result_id):
                raise ValidationError(_(
                    'A report block belongs either to a catalogue test or to a '
                    'single result, not to both and not to neither.'))

    @api.model_create_multi
    def create(self, vals_list):
        # @api.constrains only fires for fields present in vals, so a block
        # created with neither parent would slip through.
        records = super().create(vals_list)
        records._check_single_parent()
        return records

    def _copy_to_result_vals(self):
        """Values for cloning catalogue blocks onto a new result."""
        return [(0, 0, {
            'name': block.name,
            'sequence': block.sequence,
            'body_html': block.body_html,
            'style': block.style,
        }) for block in self]
