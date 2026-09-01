{
    'name': 'LEIH Payroll Custom Fields',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Contract/company fields carried over from the legacy GM payroll system, '
               'needed by the migrated salary rule formulas.',
    'description': """
Adds the employee-version and company fields that the salary rule formulas
migrated from the old GM (Odoo 8) payroll system reference:
hr.version: driver_salay, medical_insurance, supplementary_allowance, tds,
voluntary_provident_fund, x_ins, x_pf, x_tax.
res.company: dearness_allowance.
""",
    'author': 'Kazi Alamin',
    'license': 'LGPL-3',
    'depends': ['hr_payroll_community'],
    'data': [
        'views/hr_version_views.xml',
    ],
    'installable': True,
    'application': False,
}
