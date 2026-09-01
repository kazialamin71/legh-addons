from odoo import fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    driver_salay = fields.Boolean(
        string='Driver Salary',
        help='Check this box if you provide allowance for driver')
    medical_insurance = fields.Float(
        string='Medical Insurance',
        help='Deduction towards company provided medical insurance')
    supplementary_allowance = fields.Float(string='Supplementary Allowance')
    tds = fields.Float(
        string='TDS', help='Amount for Tax Deduction at Source')
    voluntary_provident_fund = fields.Float(
        string='Voluntary Provident Fund (%)',
        help='VPF is a safe option wherein you can contribute more than the '
             'PF ceiling of 12%% that has been mandated by the government '
             'and VPF computed as percentage(%%)')
    x_ins = fields.Float(string='Group Ins.')
    x_pf = fields.Float(string='Provident Fund')
    x_tax = fields.Float(string='Income Tax')

    def get_all_structures(self):
        """hr_payroll_community's get_all_structures() reads
        contract_template_id.struct_id, which is normally unset, instead of
        the version's own struct_id -- so payslips always compute zero
        lines. Use struct_id directly instead."""
        structures = self.mapped('struct_id')
        if not structures:
            return []
        return list(set(structures._get_parent_structure().ids))
