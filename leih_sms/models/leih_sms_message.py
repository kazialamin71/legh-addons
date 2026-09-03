from odoo import fields, models


class LeihSmsMessage(models.Model):
    """One row per message attempted.

    Texts cost money and gateways fail quietly, so "was the patient actually
    told?" has to be answerable months later. The raw number is kept alongside
    the normalised one because a message that went to the wrong phone is
    usually a number that was typed oddly, and the original is the evidence.
    """
    _name = 'leih.sms.message'
    _description = 'SMS Message'
    _order = 'create_date desc, id desc'
    _rec_name = 'number'

    number = fields.Char('Sent To', readonly=True, index=True)
    number_raw = fields.Char('As Entered', readonly=True)
    body = fields.Text('Message', readonly=True)
    state = fields.Selection(
        [('draft', 'Pending'), ('sent', 'Sent'),
         ('test', 'Test Mode'), ('failed', 'Failed')],
        default='draft', readonly=True, index=True)
    error = fields.Char('Why It Failed', readonly=True)
    response = fields.Text('Gateway Reply', readonly=True)
    sent_on = fields.Datetime('Sent On', readonly=True)
    source_model = fields.Char('Source Model', readonly=True, index=True)
    source_res_id = fields.Integer('Source Id', readonly=True, index=True)

    def _fail(self, reason):
        self.write({'state': 'failed', 'error': reason})
        return self

    def action_open_source(self):
        """Jump to the appointment or document the message came from."""
        self.ensure_one()
        if not self.source_model or not self.source_res_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.source_model,
            'res_id': self.source_res_id,
            'view_mode': 'form',
            'target': 'current',
        }
