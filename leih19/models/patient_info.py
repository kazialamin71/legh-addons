from odoo import models, fields, api


class PatientInfo(models.Model):
    _name = 'patient.info'
    _description = 'PatientInfo'

    mobile = fields.Char('Mobile No')
    patient_id = fields.Char('Patient Id', readonly=True, copy=False)
    name = fields.Char('Name', required=True)
    age = fields.Char('Age')
    address = fields.Char('Address', required=True)
    sex = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('others', 'Others')
    ], string='Sex', default='male')

    photo = fields.Image('Photo')
    bills = fields.One2many('bill.register', 'patient_name', required=False)
    testname = fields.Char('Test Name')
    state = fields.Selection([
        ('created', 'Created'),
        ('notcreated', 'Notcreated')
    ], 'Status', default='notcreated', readonly=True)

    bill_count = fields.Integer(string="Bills", compute="_compute_bill_count")

    # Front desk looks patients up by phone number at least as often as by name,
    # and a name alone is rarely unique, so make both (plus the patient id)
    # searchable from any Many2one to patient.info.
    _rec_names_search = ['name', 'mobile', 'patient_id']

    @api.depends('name', 'mobile', 'patient_id')
    @api.depends_context('patient_display_contact')
    def _compute_display_name(self):
        """Show ``Name [ID] - Mobile`` where the extra context flag is set.

        Only the registration/billing forms opt in via ``patient_display_contact``;
        reports and everything else keep the plain patient name.
        """
        if not self.env.context.get('patient_display_contact'):
            return super()._compute_display_name()
        for rec in self:
            label = rec.name or ''
            if rec.patient_id:
                label = '%s [%s]' % (label, rec.patient_id)
            if rec.mobile:
                label = '%s - %s' % (label, rec.mobile)
            rec.display_name = label

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('patient_id'):
                vals['patient_id'] = self.env['ir.sequence'].next_by_code('patient.info') or '/'
        return super().create(vals_list)

    def _compute_bill_count(self):
        Bill = self.env['bill.register']
        for rec in self:
            rec.bill_count = Bill.search_count([('patient_name', '=', rec.id)])

    def action_view_bills(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bills',
            'res_model': 'bill.register',
            'view_mode': 'list,form',
            'domain': [('patient_name', '=', self.id)],
            'context': {'default_patient_name': self.id},
        }