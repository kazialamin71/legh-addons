from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EmergencyDispositionWizard(models.TransientModel):
    """Close an ED case with an outcome.

    Every ED visit ends in exactly one of these, and which one is chosen decides
    what else has to happen: an admission record for "Admitted", a destination
    for "Transferred Out", and -- for the outcomes where the patient simply
    leaves -- a decision about money still outstanding.
    """
    _name = 'emergency.disposition.wizard'
    _description = 'ED Disposition'

    case_id = fields.Many2one(
        'emergency.case', string='ED Case', required=True,
        ondelete='cascade', readonly=True)
    disposition = fields.Selection(
        [('discharged', 'Discharged Home'),
         ('admitted', 'Admitted to Ward'),
         ('transferred', 'Transferred Out'),
         ('lwbs', 'Left Without Being Seen'),
         ('absconded', 'Absconded'),
         ('died', 'Died in ED'),
         ('brought_dead', 'Brought in Dead')],
        string='Disposition', required=True, default='discharged')
    note = fields.Char('Note')
    transferred_to = fields.Char('Transferred To')

    due = fields.Float(related='case_id.due', readonly=True)
    collect_now = fields.Float('Collect Now')
    payment_type = fields.Many2one('payment.type', string='Payment Type')
    # An ED cannot hold a patient for an unpaid bill, so leaving with a balance
    # has to be possible -- but as a deliberate, recorded choice.
    waive_due = fields.Boolean(
        'Close With Outstanding Due',
        help='Close the case even though money is still owed. Use for cases '
             'that leave without settling; the due stays on record.')
    waive_reason = fields.Char('Reason')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        case = self.env['emergency.case'].browse(
            res.get('case_id') or self.env.context.get('default_case_id'))
        if case.exists():
            res.setdefault('collect_now', case.due if case.due > 0 else 0.0)
            res.setdefault('payment_type', case.payment_type.id or False)
            if case.state == 'arrived':
                # Never seen by a doctor: the only outcomes that make sense are
                # the ones where the patient left on their own.
                res.setdefault('disposition', 'lwbs')
        return res

    def action_confirm(self):
        self.ensure_one()
        case = self.case_id
        if case.state == 'closed':
            raise UserError(_('This case is already closed.'))

        if self.disposition == 'transferred' and not (self.transferred_to or '').strip():
            raise UserError(_('Name the facility the patient is transferred to.'))

        if self.collect_now:
            case._register_ed_payment(self.collect_now, self.payment_type)

        remaining = case.due
        if remaining > 0.01 and not self.waive_due:
            raise UserError(_(
                '%(due).2f is still outstanding on this case.\n\n'
                'Collect it, or tick "Close With Outstanding Due" to close '
                'anyway and leave the balance on record.', due=remaining))
        if self.waive_due and remaining > 0.01 and not (self.waive_reason or '').strip():
            raise UserError(_('Give a reason for closing with an unpaid balance.'))

        vals = {
            'state': 'closed',
            'disposition': self.disposition,
            'disposition_time': fields.Datetime.now(),
            'disposition_note': self.note or self.waive_reason or False,
            'transferred_to': self.transferred_to or False,
        }
        case.write(vals)

        if self.disposition == 'admitted':
            admission = case._create_admission()
            return {
                'type': 'ir.actions.act_window',
                'name': _('Admission'),
                'res_model': 'hospital.admission',
                'view_mode': 'form',
                'res_id': admission.id,
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}
