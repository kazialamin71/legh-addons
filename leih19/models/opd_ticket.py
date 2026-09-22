from odoo import models, fields, api, _
from odoo.exceptions import UserError

class OpdTicket(models.Model):
    _name = 'opd.ticket'
    _description = 'OpdTicket'
    _order = 'date desc, id desc'

    # The ticket number the counter hands the patient. It used to be a free text
    # field nobody filled in -- tickets ended up named after the patient, or not
    # at all -- so it is now drawn from a sequence (OPD-00001) like every other
    # money document in LEIS.
    name = fields.Char('Ticket No', readonly=True, copy=False, index=True, default='New')
    patient_name = fields.Many2one('patient.info', string='Patient Name')
    patient_id = fields.Char(related='patient_name.patient_id', string='Patient Id', readonly=True)

    # Patient details mirrored from the selected patient. They used to be plain
    # non-stored Char fields that nothing ever filled in, so the form, the list
    # and the OPD ticket printout all showed them empty.
    mobile = fields.Char(string='Mobile', compute='_compute_patient_details')
    address = fields.Char('Address', compute='_compute_patient_details')
    age = fields.Char('Age', compute='_compute_patient_details')
    sex = fields.Char('Sex', compute='_compute_patient_details')
    already_collected = fields.Boolean('Money Collected', default=False, copy=False)
    # A ticket with no date fell onto whatever day its create_date happened to
    # be in the collection report, so it defaults to today and stays editable.
    date = fields.Date('Date', default=fields.Date.context_today, copy=False)
    ref_doctors = fields.Many2one('doctors.profile', string='Doctor name')
    opd_ticket_line_id = fields.One2many('opd.ticket.line', 'opd_ticket_id', required=True)
    # How the money came in. Decides which account the ticket's journal entry
    # debits and which sheet its receipt collects onto; left empty it falls back
    # to the OPD section's default payment type.
    payment_type = fields.Many2one('payment.type', string='Payment Type')
    user_id = fields.Many2one('res.users', string='Assigned to', index=True,
                              default=lambda self: self.env.user)
    state = fields.Selection([('confirmed', 'Confirmed'), ('cancelled', 'Cancelled')],
                             'Status', default='confirmed', readonly=True, copy=False)
    total = fields.Float(string='Total', compute='_compute_total', store=True)
    with_doctor_total = fields.Float(string='Total with Doctor Fee')


    prescription_count = fields.Integer(string='Prescription Count', compute='_compute_prescription_count')

    # Writing any of these can change how much money the ticket stands for, or
    # where that money should be booked.
    _MONEY_FIELDS = frozenset({'state', 'opd_ticket_line_id', 'payment_type', 'date'})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('opd.ticket') or 'New'
        tickets = super().create(vals_list)
        tickets._settle_ticket_money()
        return tickets

    def write(self, vals):
        result = super().write(vals)
        if self._MONEY_FIELDS & set(vals):
            self._settle_ticket_money()
        return result

    def _settle_ticket_money(self):
        """Run whenever a ticket's amount settles. Extension point, no-op here.

        leih_cash_collection_auto issues the money receipt from this, and
        leih_accounting posts the journal entry. It has to be a hook rather than
        a ``write`` override in those modules: ``total`` is a stored computed
        field, so a ticket saved empty and given its items afterwards recomputes
        the total without ``total`` ever appearing in a ``write`` -- which is
        exactly why such tickets used to get neither a receipt nor an entry.
        Called again from opd.ticket.line, for items edited from their own view.
        """
        return

    @api.depends('opd_ticket_line_id.total_amount')
    def _compute_total(self):
        for rec in self:
            rec.total = sum(rec.opd_ticket_line_id.mapped('total_amount'))

    @api.depends('patient_name')
    def _compute_patient_details(self):
        sex_labels = dict(self.env['patient.info']._fields['sex'].selection)
        for rec in self:
            patient = rec.patient_name
            rec.mobile = patient.mobile or False
            rec.address = patient.address or False
            rec.age = patient.age or False
            rec.sex = sex_labels.get(patient.sex, patient.sex) or False

    def _compute_prescription_count(self):
        Prescription = self.env['doctor.prescription']
        for rec in self:
            rec.prescription_count = Prescription.search_count([('opd_ticket_id', '=', rec.id)])

    # ---------------------------------------------------------------- workflow
    def action_cancel(self):
        """Void the ticket: its money leaves the collection and its entries are
        reversed.

        The modules that gave the ticket a money receipt (leih_cash_collection_auto)
        and a journal entry (leih_accounting) extend this, so cancelling here is
        the one place that undoes all three. Cancelling is final -- the money has
        already been reported -- so a ticket cancelled by mistake is replaced by
        a new one rather than reopened.
        """
        for rec in self:
            if rec.state == 'cancelled':
                raise UserError(_('%s is already cancelled.') % rec.display_name)
        self.write({'state': 'cancelled', 'already_collected': False})
        return True

    def action_create_prescription(self):
        self.ensure_one()
        if self.state == 'cancelled':
            raise UserError(_('This ticket is cancelled.'))
        if not self.patient_name:
            raise UserError(_('Please select a patient first.'))
        if not self.ref_doctors:
            raise UserError(_('Please select a doctor first.'))
        prescription = self.env['doctor.prescription'].create({
            'patient_id': self.patient_name.id,
            'doctor_id': self.ref_doctors.id,
            'department': self.opd_ticket_line_id[:1].department or self.ref_doctors.department,
            'source_model': 'opd.ticket',
            'opd_ticket_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Prescription'),
            'res_model': 'doctor.prescription',
            'view_mode': 'form',
            'res_id': prescription.id,
            'target': 'current',
        }

    def action_view_prescriptions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Prescriptions'),
            'res_model': 'doctor.prescription',
            'view_mode': 'list,form',
            'domain': [('opd_ticket_id', '=', self.id)],
            'context': {
                'default_patient_id': self.patient_name.id,
                'default_doctor_id': self.ref_doctors.id,
                'default_opd_ticket_id': self.id,
                'default_source_model': 'opd.ticket',
            },
        }
