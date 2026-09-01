from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# Time-to-be-seen targets, in minutes, for the three triage levels. Kept here
# rather than on a configuration model because they are clinical convention, not
# a per-hospital preference -- and a queue that silently reorders when someone
# edits a setting is worse than one that never moves.
TRIAGE_TARGETS = {
    'critical': 0,
    'urgent': 30,
    'standard': 120,
}


class EmergencyCase(models.Model):
    """One visit to the emergency department.

    Deliberately NOT a flag on ``hospital.admission``. Most ED patients are
    treated and sent home, so modelling emergency as an urgent admission would
    force an admission record -- and eventually a bed -- for people who never
    occupy one. An admission is created here only when the disposition really is
    "Admitted".

    Registration never blocks care: a collapsed patient with no name is
    registered from a typed description alone, and reconciled to a real
    ``patient.info`` once somebody can give one.
    """
    _name = 'emergency.case'
    _description = 'Emergency Case'
    # The board is read top-down in the order patients should be seen:
    # sickest first, then longest waiting.
    _order = 'triage_sequence, arrival_time'
    _rec_name = 'name'

    name = fields.Char('ED No.', default='New', copy=False, readonly=True, index=True)

    # ------------------------------------------------------------------
    # Identity -- typed first, linked later
    # ------------------------------------------------------------------
    patient_id = fields.Many2one(
        'patient.info', string='Patient', copy=False, index=True, readonly=True,
        help='The hospital patient record. Empty until someone can identify the '
             'patient; registration never waits for it.')
    hn_number = fields.Char(
        'Hospital No.', related='patient_id.patient_id', readonly=True)
    patient_name = fields.Char(
        'Patient Name', required=True,
        help='A description is enough when the name is unknown, e.g. '
             '"Unknown male, approx 40".')
    age = fields.Char('Age')
    sex = fields.Selection(
        [('male', 'Male'), ('female', 'Female'), ('others', 'Others'),
         ('unknown', 'Unknown')], string='Sex', default='unknown')
    mobile = fields.Char('Mobile No.')
    address = fields.Char('Address')

    attendant_name = fields.Char('Attendant / Guardian')
    attendant_contact = fields.Char('Attendant Contact')

    # ------------------------------------------------------------------
    # Arrival
    # ------------------------------------------------------------------
    arrival_time = fields.Datetime(
        'Arrival Time', default=fields.Datetime.now, required=True, index=True)
    arrival_mode = fields.Selection(
        [('walk_in', 'Walk-in'),
         ('ambulance', 'Ambulance'),
         ('referral', 'Referred'),
         ('police', 'Police / Rescue')],
        string='Arrival Mode', default='walk_in', required=True)
    referred_from = fields.Char('Referred From')
    chief_complaint = fields.Text('Chief Complaint')

    # ------------------------------------------------------------------
    # Triage
    # ------------------------------------------------------------------
    triage_level = fields.Selection(
        [('critical', 'Critical (Red)'),
         ('urgent', 'Urgent (Yellow)'),
         ('standard', 'Non-urgent (Green)')],
        string='Triage Level', index=True, copy=False, tracking=True)
    # Stored so the board can sort on it in SQL. A Selection sorts
    # alphabetically, which would put Critical after both the others.
    triage_sequence = fields.Integer(
        compute='_compute_triage_sequence', store=True, index=True)
    triage_time = fields.Datetime('Triaged At', readonly=True, copy=False)
    triaged_by = fields.Many2one('res.users', string='Triaged By', readonly=True, copy=False)

    # Vitals, taken at triage.
    bp_systolic = fields.Integer('BP Systolic')
    bp_diastolic = fields.Integer('BP Diastolic')
    pulse = fields.Integer('Pulse (/min)')
    respiratory_rate = fields.Integer('Resp. Rate (/min)')
    temperature = fields.Float('Temp (deg F)')
    spo2 = fields.Integer('SpO2 (%)')
    gcs = fields.Integer('GCS', help='Glasgow Coma Scale, 3-15.')

    # ------------------------------------------------------------------
    # Treatment
    # ------------------------------------------------------------------
    attending_doctor = fields.Many2one('doctors.profile', string='Attending Doctor')
    treatment_start = fields.Datetime('Treatment Started', readonly=True, copy=False)
    treatment_note = fields.Text('Treatment / Clinical Note')
    provisional_diagnosis = fields.Char('Provisional Diagnosis')

    # ------------------------------------------------------------------
    # Medico-legal
    # ------------------------------------------------------------------
    is_medico_legal = fields.Boolean(
        'Medico-Legal Case',
        help='Road accident, assault, poisoning, burn or any case the police '
             'must be informed about.')
    mlc_type = fields.Selection(
        [('rta', 'Road Traffic Accident'),
         ('assault', 'Assault'),
         ('poisoning', 'Poisoning'),
         ('burn', 'Burn'),
         ('self_harm', 'Self-harm'),
         ('other', 'Other')], string='MLC Type')
    police_station = fields.Char('Police Station')
    gd_number = fields.Char('GD / Case No.')
    informed_officer = fields.Char('Officer Informed')

    # ------------------------------------------------------------------
    # Money -- charges, then settlement at disposition
    # ------------------------------------------------------------------
    charge_ids = fields.One2many(
        'emergency.case.charge', 'case_id', string='Charges')
    money_receipt_ids = fields.One2many(
        'leih.money.receipt', 'emergency_case_id', string='Money Receipts')
    total_charges = fields.Float(
        'Total Charges', compute='_compute_amounts', store=True)
    paid = fields.Float('Paid', compute='_compute_amounts', store=True)
    due = fields.Float('Due', compute='_compute_amounts', store=True)
    payment_type = fields.Many2one('payment.type', string='Payment Type')

    # ------------------------------------------------------------------
    # State and outcome
    # ------------------------------------------------------------------
    state = fields.Selection(
        [('arrived', 'Arrived'),
         ('triaged', 'Triaged'),
         ('in_treatment', 'In Treatment'),
         ('closed', 'Closed'),
         ('cancelled', 'Cancelled')],
        string='Status', default='arrived', required=True, index=True,
        copy=False, tracking=True)
    disposition = fields.Selection(
        [('discharged', 'Discharged Home'),
         ('admitted', 'Admitted to Ward'),
         ('transferred', 'Transferred Out'),
         ('lwbs', 'Left Without Being Seen'),
         ('absconded', 'Absconded'),
         ('died', 'Died in ED'),
         ('brought_dead', 'Brought in Dead')],
        string='Disposition', readonly=True, copy=False, index=True)
    disposition_time = fields.Datetime('Disposition At', readonly=True, copy=False)
    disposition_note = fields.Char('Disposition Note', readonly=True, copy=False)
    transferred_to = fields.Char('Transferred To', readonly=True, copy=False)
    admission_id = fields.Many2one(
        'hospital.admission', string='Admission', readonly=True, copy=False,
        help='Created when the patient is admitted to a ward from the ED.')

    # ------------------------------------------------------------------
    # Waiting / breach
    # ------------------------------------------------------------------
    target_minutes = fields.Integer(
        'Target (min)', compute='_compute_waiting',
        help='How long this triage level may wait to be seen.')
    waiting_minutes = fields.Integer('Waiting (min)', compute='_compute_waiting')
    waiting_display = fields.Char('Waiting', compute='_compute_waiting')
    is_breached = fields.Boolean(
        'Target Breached', compute='_compute_waiting',
        search='_search_is_breached',
        help='Waiting longer than the triage level allows.')

    @api.depends('triage_level')
    def _compute_triage_sequence(self):
        order = {'critical': 1, 'urgent': 2, 'standard': 3}
        for rec in self:
            # Untriaged patients sort above everyone: nobody knows yet how sick
            # they are, which is itself the most urgent thing on the board.
            rec.triage_sequence = order.get(rec.triage_level, 0)

    @api.depends('arrival_time', 'triage_level', 'state', 'treatment_start')
    def _compute_waiting(self):
        now = fields.Datetime.now()
        for rec in self:
            target = TRIAGE_TARGETS.get(rec.triage_level, 0)
            rec.target_minutes = target
            # The clock stops when the doctor picks the patient up; after that
            # "waiting" is meaningless and a breach flag is just noise.
            if rec.state in ('closed', 'cancelled') or rec.treatment_start or not rec.arrival_time:
                rec.waiting_minutes = 0
                rec.waiting_display = ''
                rec.is_breached = False
                continue
            minutes = max(0, int((now - rec.arrival_time).total_seconds() // 60))
            rec.waiting_minutes = minutes
            rec.waiting_display = (
                '%d min' % minutes if minutes < 60
                else '%dh %02dm' % divmod(minutes, 60))
            rec.is_breached = bool(rec.triage_level) and minutes > target

    def _search_is_breached(self, operator, value):
        """Make the breach flag filterable even though it is not stored.

        It cannot be stored: it depends on the current time, so a stored column
        would be stale the moment it was written and would need a cron to stay
        honest. Instead the filter is rewritten into a domain on arrival_time,
        one branch per triage level, using each level's own target.
        """
        if operator not in ('=', '!='):
            raise NotImplementedError(
                _('Only = and != are supported on "Target Breached".'))
        breached = bool(value) if operator == '=' else not value

        now = fields.Datetime.now()
        # Still waiting to be seen: open, triaged, nobody has picked them up.
        # Written in prefix notation by hand rather than through a domain
        # helper: odoo.osv is deprecated in 19.0 and this is three ANDs.
        waiting = [
            '&', '&',
            ('state', 'in', ('arrived', 'triaged')),
            ('treatment_start', '=', False),
            ('triage_level', '!=', False),
        ]
        over_target = []
        for level, target in TRIAGE_TARGETS.items():
            branch = ['&', ('triage_level', '=', level),
                      ('arrival_time', '<', now - timedelta(minutes=target))]
            over_target = ['|'] + over_target + branch if over_target else branch

        domain = ['&'] + waiting + over_target
        if breached:
            return domain
        return ['!'] + domain

    @api.depends('charge_ids.total_amount',
                 'money_receipt_ids.amount', 'money_receipt_ids.state')
    def _compute_amounts(self):
        for rec in self:
            rec.total_charges = sum(rec.charge_ids.mapped('total_amount'))
            rec.paid = sum(
                rec.money_receipt_ids
                .filtered(lambda m: m.state == 'confirm')
                .mapped('amount'))
            rec.due = rec.total_charges - rec.paid

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in ('New', False):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'emergency.case') or 'New'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Flow
    # ------------------------------------------------------------------
    def action_confirm_triage(self):
        """Record the triage decision and put the patient on the board."""
        for rec in self:
            if not rec.triage_level:
                raise UserError(_(
                    'Set the triage level before confirming triage.'))
            if rec.state in ('closed', 'cancelled'):
                raise UserError(_('This case is already closed.'))
            rec.triage_time = rec.triage_time or fields.Datetime.now()
            rec.triaged_by = rec.triaged_by or self.env.user
            if rec.state == 'arrived':
                rec.state = 'triaged'
        return True

    def action_start_treatment(self):
        """Doctor picks the patient up; the waiting clock stops here."""
        self.ensure_one()
        if not self.triage_level:
            raise UserError(_('Triage this patient before starting treatment.'))
        if self.state in ('closed', 'cancelled'):
            raise UserError(_('This case is already closed.'))
        if not self.attending_doctor:
            raise UserError(_('Select the attending doctor first.'))
        self.treatment_start = self.treatment_start or fields.Datetime.now()
        self.state = 'in_treatment'
        return True

    def action_open_disposition(self):
        """Close the case with an outcome."""
        self.ensure_one()
        if self.state == 'closed':
            raise UserError(_(
                '%(case)s was already closed as "%(outcome)s".',
                case=self.name,
                outcome=dict(self._fields['disposition'].selection).get(
                    self.disposition, '-')))
        if self.state == 'cancelled':
            raise UserError(_('This case is cancelled.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Disposition'),
            'res_model': 'emergency.disposition.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_case_id': self.id},
        }

    def action_collect_payment(self):
        self.ensure_one()
        if self.due <= 0:
            raise UserError(_('There is nothing outstanding on this case.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Collect Payment'),
            'res_model': 'emergency.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_case_id': self.id,
                        'default_amount': self.due},
        }

    def action_cancel(self):
        for rec in self:
            if rec.state == 'closed':
                raise UserError(_('A closed case cannot be cancelled.'))
            rec.state = 'cancelled'
        return True

    def action_reset_to_triaged(self):
        """Reopen a case closed by mistake, leaving the money alone."""
        for rec in self:
            if rec.admission_id:
                raise UserError(_(
                    'This case was admitted as %(adm)s. Cancel that admission '
                    'first.', adm=rec.admission_id.name))
            rec.write({'state': 'triaged' if rec.triage_level else 'arrived',
                       'disposition': False, 'disposition_time': False,
                       'disposition_note': False, 'transferred_to': False})
        return True

    # ------------------------------------------------------------------
    # Patient record / admission
    # ------------------------------------------------------------------
    def _register_patient(self):
        """Create the hospital patient record from what the ED has captured.

        Address is mandatory on patient.info; an ED patient often has none on
        arrival, so a placeholder is used rather than refusing to register
        someone who is being treated.
        """
        self.ensure_one()
        if self.patient_id:
            return self.patient_id
        patient = self.env['patient.info'].create({
            'name': self.patient_name,
            'age': self.age or False,
            'sex': self.sex if self.sex in ('male', 'female', 'others') else 'others',
            'mobile': self.mobile or False,
            'address': self.address or _('Not recorded (ED)'),
        })
        self.patient_id = patient
        return patient

    def action_register_patient(self):
        """Give this ED patient a hospital number once they can be identified."""
        self.ensure_one()
        if self.patient_id:
            raise UserError(_(
                'This case already points at %(name)s [%(hn)s].',
                name=self.patient_id.name, hn=self.patient_id.patient_id))
        patient = self._register_patient()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Patient'),
            'res_model': 'patient.info',
            'view_mode': 'form',
            'res_id': patient.id,
            'target': 'current',
        }

    def _create_admission(self):
        """Open a ward admission seeded from this ED case.

        Left in its draft state on purpose: the ward assigns the bed and
        confirms. Admitting from here would confirm an admission with no bed.
        """
        self.ensure_one()
        patient = self._register_patient()
        admission = self.env['hospital.admission'].create({
            'patient_name': patient.id,
            'mobile': self.mobile or patient.mobile or False,
            'address': self.address or patient.address or False,
            'age': self.age or patient.age or False,
            'sex': self.sex if self.sex != 'unknown' else False,
            'admitting_doctor': self.attending_doctor.id or False,
            'ref_doctors': self.attending_doctor.id or False,
            'clinic_diagnosis': self.provisional_diagnosis or False,
            'emergency': True,
            'emergency_covert_time': fields.Datetime.now(),
            'guardian_name': self.attendant_name or False,
            'guardian_contact': self.attendant_contact or False,
        })
        self.admission_id = admission
        return admission

    def action_open_admission(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hospital.admission',
            'view_mode': 'form',
            'res_id': self.admission_id.id,
            'target': 'current',
        }

    def action_print_ed_slip(self):
        self.ensure_one()
        return self.env.ref(
            'leih_emergency.action_report_emergency_case').report_action(self)

    # ------------------------------------------------------------------
    def _register_ed_payment(self, amount, payment_type=None, date=None):
        """Take money against this ED case.

        Writes a ``leih.money.receipt`` -- the system's universal receipt -- so
        ED cash lands in the same collection reporting as every other counter.
        """
        self.ensure_one()
        amount = amount or 0.0
        if amount <= 0:
            return self.env['leih.money.receipt']
        if amount > (self.due or 0.0) + 0.01:
            raise UserError(_(
                'Payment (%(paid)s) exceeds the outstanding amount (%(due)s).',
                paid=amount, due=self.due or 0.0))
        ptype = payment_type or self.payment_type
        receipt = self.env['leih.money.receipt'].create({
            'date': date or fields.Date.context_today(self),
            'emergency_case_id': self.id,
            'amount': amount,
            'bill_total_amount': self.total_charges or 0.0,
            'due_amount': (self.due or 0.0) - amount,
            'p_type': 'due_payment' if (self.paid or 0.0) > 0 else 'advance',
            'already_collected': True,
            'payment_type': ptype.id if ptype else False,
            'user_id': self.env.user.id,
        })
        return receipt
