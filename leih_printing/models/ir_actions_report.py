import base64
import logging

from odoo import _, models
# The *wrapped* time module: safe_eval refuses a raw one, and report
# expressions are allowed to call time.strftime.
from odoo.tools.safe_eval import safe_eval, time

_logger = logging.getLogger(__name__)

# Past this, pushing the PDF through the JSON-RPC reply is the wrong tool: a
# 400-page collection report is something you download, not something anyone
# stands at a counter and prints. Falls back to the normal download.
MAX_INLINE_PDF = 8 * 1024 * 1024

# The action type our own JS handler is registered against.
PRINT_ACTION_TYPE = 'leih_printing.print'


class IrActionsReport(models.Model):
    """Route every PDF report through the user's "Print via" setting.

    Applied here rather than on individual reports on purpose: the desk should
    not have to remember that a bill prints one way and a lab report another.
    Anything that is not a ``qweb-pdf``, and anything asked for with
    ``leih_force_download`` in the context, is left completely alone.
    """
    _inherit = 'ir.actions.report'

    def report_action(self, docids, data=None, config=True):
        action = super().report_action(docids, data=data, config=config)
        return self._route_to_printer(action, docids, data)

    @staticmethod
    def _normalise_docids(docids):
        if not docids:
            return []
        if isinstance(docids, models.Model):
            return docids.ids
        if isinstance(docids, int):
            return [docids]
        return list(docids)

    def _route_to_printer(self, action, docids, data):
        if len(self) != 1 or action.get('type') != 'ir.actions.report':
            # The "configure your report layout" branch returns a different
            # action entirely. Touching it would lock an admin out of ever
            # setting the layout.
            return action
        if action.get('report_type') != 'qweb-pdf':
            return action
        if self.env.context.get('leih_force_download'):
            return action

        user = self.env.user
        mode = user.print_mode
        if mode == 'download':
            return action

        res_ids = self._normalise_docids(docids)
        report = self.with_context(**action.get('context') or {})
        try:
            pdf, _ext = report._render_qweb_pdf(
                self.report_name, res_ids=res_ids, data=data)
        except Exception:
            # A report that cannot render cannot be downloaded either, so there
            # is nothing to fall back to -- but say which report it was, because
            # the traceback alone does not.
            _logger.exception('Could not render %s for printing', self.report_name)
            raise

        title = self._report_title(res_ids)
        if mode == 'server':
            return self._print_on_server(user, pdf, title, action)
        return self._print_on_client(pdf, title, action)

    def _report_title(self, res_ids):
        """The name on the CUPS job and on the browser's print job.

        Same expression, and the same eval context, the download controller uses
        to build the filename -- so a job in the CUPS queue is named the way the
        file used to be, and the desk can still recognise it.
        """
        self.ensure_one()
        if self.print_report_name and res_ids and self.model:
            record = self.env[self.model].browse(res_ids[:1])
            try:
                return str(safe_eval(self.print_report_name,
                                     {'object': record, 'time': time}))
            except Exception:  # noqa: BLE001 - a bad name must never stop a print
                _logger.warning('print_report_name of %s could not be evaluated',
                                self.report_name)
        return self.name or self.report_name

    # ------------------------------------------------------------------
    def _print_on_server(self, user, pdf, title, action):
        printer = user.printer_id
        if not printer:
            # The constraint normally prevents this, but a printer that was
            # archived out from under the user would land here.
            _logger.warning('User %s prints server-side but has no printer; '
                            'falling back to a download.', user.login)
            return action
        printer.print_document(pdf, title)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sent to the printer'),
                'message': _('%(document)s went to %(printer)s.',
                             document=title, printer=printer.name),
                'type': 'success',
                'next': ({'type': 'ir.actions.act_window_close'}
                         if action.get('close_on_report_download') else None),
            },
        }

    def _print_on_client(self, pdf, title, action):
        if len(pdf) > MAX_INLINE_PDF:
            _logger.info('%s is %s bytes, too big to print inline; downloading '
                         'instead.', self.report_name, len(pdf))
            return action
        return {
            'type': PRINT_ACTION_TYPE,
            'name': title,
            'pdf': base64.b64encode(pdf).decode(),
            'close': bool(action.get('close_on_report_download')),
        }
