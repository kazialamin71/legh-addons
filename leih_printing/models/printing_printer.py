import logging
import re
import shutil
import subprocess

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# `lp` returns as soon as CUPS has *spooled* the job, so this is normally
# instant. The timeout is there for the case that matters at a counter: a
# printer that is switched off or off the network. The desk gets an error it can
# read instead of a frozen browser tab.
LP_TIMEOUT = 20

# "printer HP_LaserJet_Pro_4003_B65769 is idle.  enabled since Mon 31 Aug ..."
# The status sentence is followed by more text, so anchoring at the end of the
# line matches nothing at all.
_PRINTER_RE = re.compile(r'^printer\s+(?P<queue>\S+)\s+is\s+(?P<status>[^.]+)\.')
_DETAIL_RE = re.compile(r'^\s+(?P<key>Description|Location):\s*(?P<value>.*)$')


class PrintingPrinter(models.Model):
    """A CUPS print queue the *server* can reach.

    Only queues registered here can be printed to server-side. A printer plugged
    into a counter PC over USB is not one of these and never will be -- the
    server has no path to it -- which is what the per-user "This computer" mode
    is for.
    """
    _name = 'printing.printer'
    _description = 'CUPS Printer'
    _order = 'name'

    name = fields.Char(required=True)
    system_name = fields.Char(
        'CUPS Queue', required=True, index=True,
        help='The queue name exactly as CUPS knows it -- what "lpstat -p" '
             'prints. This is the address the job is sent to; a typo here is a '
             'job that vanishes.')
    location = fields.Char('Location', help='Where the paper physically comes out.')
    info = fields.Char('Last Known Status', readonly=True)
    options = fields.Char(
        'lp Options',
        help='Extra options passed to lp, space separated, each without its '
             '-o. For example: media=A4 sides=one-sided. Leave empty to use '
             "the printer's own defaults.")
    active = fields.Boolean(default=True)

    _system_name_uniq = models.Constraint(
        'UNIQUE (system_name)',
        'That CUPS queue is already registered.')

    # ------------------------------------------------------------------
    # Talking to CUPS
    # ------------------------------------------------------------------
    @api.model
    def _cups_available(self):
        return bool(shutil.which('lp') and shutil.which('lpstat'))

    @api.model
    def _run(self, argv, stdin=None):
        """Run a CUPS command, turning every failure into a readable UserError."""
        if not self._cups_available():
            raise UserError(_(
                'CUPS is not installed on the Odoo server, so it cannot send '
                'anything to a printer. Either install it, or set "Print via" '
                'to "This computer" on the user.'))
        try:
            proc = subprocess.run(
                argv, input=stdin, capture_output=True, timeout=LP_TIMEOUT,
                check=False)
        except subprocess.TimeoutExpired:
            raise UserError(_(
                'The printer did not answer within %(seconds)s seconds. It is '
                'most likely switched off or off the network.',
                seconds=LP_TIMEOUT))
        except OSError as err:
            raise UserError(_('Could not run %(cmd)s: %(err)s',
                              cmd=argv[0], err=err))
        if proc.returncode:
            raise UserError(_(
                'The printer refused the job:\n\n%(error)s',
                error=(proc.stderr or proc.stdout).decode('utf-8', 'replace').strip()
                      or _('no reason given')))
        return proc.stdout.decode('utf-8', 'replace').strip()

    @api.model
    def _cups_queues(self):
        """[(queue, status, description, location)] as CUPS currently reports."""
        output = self._run(['lpstat', '-l', '-p'])
        queues, current = [], None
        for line in output.splitlines():
            match = _PRINTER_RE.match(line)
            if match:
                current = {'queue': match['queue'], 'status': match['status'],
                           'description': '', 'location': ''}
                queues.append(current)
                continue
            detail = _DETAIL_RE.match(line)
            if detail and current:
                current[detail['key'].lower()] = detail['value'].strip()
        return queues

    def action_sync_from_cups(self):
        """Create or refresh a record for every queue the server can see.

        Never deletes: a printer that is unplugged for an afternoon should not
        silently take every user's printer setting with it.
        """
        found = self._cups_queues()
        created = 0
        for queue in found:
            printer = self.with_context(active_test=False).search(
                [('system_name', '=', queue['queue'])], limit=1)
            values = {'info': queue['status']}
            if not printer:
                # CUPS nearly always reports Description as the queue name over
                # again, so fall through to the tidied queue name in that case
                # too -- "HP LaserJet Pro 4003" reads off a dropdown,
                # "HP_LaserJet_Pro_4003_B65769" does not.
                description = queue['description']
                if not description or description == queue['queue']:
                    description = queue['queue'].replace('_', ' ')
                values.update({
                    'system_name': queue['queue'],
                    'name': description,
                    'location': queue['location'],
                })
                self.create(values)
                created += 1
            else:
                if not printer.location and queue['location']:
                    values['location'] = queue['location']
                printer.write(values)
        message = _('%(total)s printer(s) found, %(created)s newly added.',
                    total=len(found), created=created)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': _('Printers synced'), 'message': message,
                       'type': 'success', 'next': {'type': 'ir.actions.act_window_close'}},
        }

    def print_document(self, content, title='Odoo document'):
        """Spool `content` (PDF bytes) to this queue. Returns the CUPS job id."""
        self.ensure_one()
        argv = ['lp', '-d', self.system_name, '-t', title[:255]]
        for option in (self.options or '').split():
            argv += ['-o', option]
        argv.append('-')
        result = self._run(argv, stdin=content)
        _logger.info('Printed %r to %s: %s', title, self.system_name, result)
        return result

    def action_print_test_page(self):
        """Prove the whole path works -- Odoo, CUPS, network, paper."""
        self.ensure_one()
        html = self.env['ir.qweb']._render('leih_printing.test_page', {
            'printer': self,
            'user': self.env.user,
            'now': fields.Datetime.to_string(fields.Datetime.now()),
        })
        pdf = self.env['ir.actions.report']._run_wkhtmltopdf([html])
        self.print_document(pdf, 'Odoo test page - %s' % self.name)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Test page sent'),
                'message': _('Sent to %(printer)s. Go and see whether paper '
                             'came out.', printer=self.name),
                'type': 'success',
            },
        }
