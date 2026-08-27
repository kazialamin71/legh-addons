from odoo import fields, models


class ResCompany(models.Model):
    """Boilerplate that prints on the consultation token.

    Kept on the company rather than hard-coded in the template because these
    are policy statements - free review windows, charge percentages, the
    enquiry number - and they change without a developer being involved.
    """
    _inherit = 'res.company'

    appointment_token_notes = fields.Text(
        'Consultation Token Notes',
        help='Printed as a numbered box on the consultation token. One note '
             'per line; blank lines are ignored. Leave empty to hide the box.',
        default=lambda self: (
            'Until the date shown, one report consultation is free without appointment.\n'
            'After that date an appointment is required and the consultation charge is 50%.\n'
            'Before coming for report review, please check the availability of the '
            'consultant by dialing the hotline.'))

    appointment_token_footer = fields.Text(
        'Consultation Token Footer',
        help='Italic note printed at the very bottom of the consultation token.',
        default='N.B. - We have sent your invoice through SMS to your registered mobile number.')

    appointment_token_qr_label = fields.Char(
        'Token QR Caption',
        help='Caption printed beside the QR code on the consultation token.',
        default='For Doctor Appointment\nScan the QR Code')
