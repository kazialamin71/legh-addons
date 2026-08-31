from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

PRINT_MODES = [
    ('client', 'This computer'),
    ('server', 'Printer on the server'),
    ('download', 'Download the PDF'),
]


class ResUsers(models.Model):
    """Where this user's printouts come out.

    Deliberately on the *user*, not the company or the report. A counter is a
    person at a desk next to a printer, and that is the only thing that reliably
    determines where their paper should appear. Two people printing the same
    bill from different desks want it in two different places.
    """
    _inherit = 'res.users'

    print_mode = fields.Selection(
        PRINT_MODES, string='Print via', default='client', required=True,
        help='This computer: the browser prints on whatever printer this PC is '
             'set to use -- the option for a printer plugged in by USB.\n'
             'Printer on the server: Odoo sends the job straight to a shared '
             'printer; nothing reaches the browser.\n'
             'Download the PDF: the old behaviour, saves a file.')
    printer_id = fields.Many2one(
        'printing.printer', string='Server Printer', ondelete='set null',
        help='Which shared printer this user\'s documents come out of. '
             'Only used when "Print via" is "Printer on the server".')

    @api.constrains('print_mode', 'printer_id')
    def _check_printer_set(self):
        for user in self:
            if user.print_mode == 'server' and not user.printer_id:
                raise ValidationError(_(
                    'Choose the printer for %(user)s, or their documents have '
                    'nowhere to go.', user=user.name))

    # Let people set their own desk's printer from their profile without
    # needing Settings access -- a counter should not have to raise a ticket to
    # say which printer is next to them.
    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['print_mode', 'printer_id']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['print_mode', 'printer_id']
