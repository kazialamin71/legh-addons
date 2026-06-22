from odoo import fields, models


class LabPrintConfirm(models.TransientModel):
    _name = 'lab.print.confirm'
    _description = 'Lab Report Print Confirmation'

    bill_register_id = fields.Many2one('bill.register', readonly=True)
    message = fields.Text(readonly=True)

    def action_print(self):
        """Print only the verified/released results of the bill."""
        self.ensure_one()
        results = self.bill_register_id.lab_result_ids.filtered(
            lambda r: r.state in ('verified', 'released'))
        return self.env.ref('leih19.action_report_examination_result').report_action(results)
