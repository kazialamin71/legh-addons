from odoo import api, fields, models


class LabSpecimen(models.Model):
    _name = 'lab.specimen'
    _description = 'Lab Specimen (one physical sample tube, may carry multiple tests)'
    _order = 'collected_at desc, id desc'

    name = fields.Char('Specimen No.', readonly=True, copy=False, default='New')
    state = fields.Selection(
        [('draft', 'Draft'),
         ('collected', 'Collected'),
         ('received', 'Received in Lab'),
         ('processed', 'Processed'),
         ('cancelled', 'Cancelled')],
        default='draft', required=True, copy=False,
    )

    patient_id = fields.Many2one('patient.info', string='Patient', required=True)
    bill_register_id = fields.Many2one('bill.register', string='Bill', ondelete='set null')

    tube_color_id = fields.Many2one('tube.color', string='Tube Color')
    department_id = fields.Many2one('diagnosis.department', string='Department')

    collected_at = fields.Datetime('Collected At')
    collected_by_id = fields.Many2one('res.users', string='Collected By')
    received_at = fields.Datetime('Received At')

    result_ids = fields.One2many('examination.result', 'specimen_id', string='Lab Results')
    result_count = fields.Integer(compute='_compute_result_count')
    test_names = fields.Char(compute='_compute_test_names', string='Tests')

    note = fields.Text('Note')

    @api.depends('result_ids')
    def _compute_result_count(self):
        for rec in self:
            rec.result_count = len(rec.result_ids)

    @api.depends('result_ids.entry_id.name')
    def _compute_test_names(self):
        for rec in self:
            rec.test_names = ', '.join(rec.result_ids.mapped('entry_id.name'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('lab.specimen') or 'New'
        return super().create(vals_list)

    def action_collect(self):
        self.write({
            'state': 'collected',
            'collected_at': fields.Datetime.now(),
            'collected_by_id': self.env.user.id,
        })

    def action_receive(self):
        self.write({
            'state': 'received',
            'received_at': fields.Datetime.now(),
        })

    def action_process(self):
        self.write({'state': 'processed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

    def action_print_sticker(self):
        """Print tube sticker(s) for the selected specimen(s)."""
        return self.env.ref('leih19.action_report_lab_specimen_sticker').report_action(self)

    def action_view_results(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Results for {self.name}',
            'res_model': 'examination.result',
            'view_mode': 'list,form',
            'domain': [('specimen_id', '=', self.id)],
            'context': {'default_specimen_id': self.id},
        }
