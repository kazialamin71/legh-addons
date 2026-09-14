{
    'name': 'LEIS Team Charge',
    'summary': "Split every charge into the hospital's share and the doctor's, "
               "keep the doctor's out of income, and reconcile what is owed",
    'description': """
LEIS Team Charge
================

Part of what a patient pays was never the hospital's money. A dressing billed at
2,000 may be 1,000 for the hospital and 1,000 for the doctor; a surgery billed at
50,000 may be 35,000 for the admitting doctor's team. The patient is billed the
full amount and sees one number, but only the hospital's share is hospital
income.

This module makes that split explicit, everywhere a charge is raised:

* **Configured on the item.** Each ``examination.entry`` carries a doctor share
  -- a percentage of the line or a flat amount per unit. Enter it once and every
  admission charge and bill line built from that item inherits it.
* **The same on both sides.** Admission charges and outpatient bill lines use one
  shared implementation, so a dressing splits identically whether it happened on
  a ward or at a counter.
* **Attributed to one doctor.** The admitting doctor, or whoever is named on the
  line. The doctor divides it among their team outside this system.
* **Kept out of income.** By default the doctor's share is never posted to the
  general ledger at all, so it appears in neither the profit and loss nor the
  trial balance. Only the hospital's share is recognised.
* **Reconcilable.** One report answers, per doctor and per day: what was charged,
  what was collected, whose money it was, and what is still owed.
""",
    'version': '19.0.1.0.9',
    'author': 'Kazi Alamin',
    'category': 'Accounting',
    'depends': ['leih_accounting', 'leih_admission', 'leih19'],
    'data': [
        'security/ir.model.access.csv',
        'views/examination_entry_views.xml',
        'views/admission_charge_item_views.xml',
        'views/doctors_profile_views.xml',
        'views/accounting_config_views.xml',
        'views/hospital_admission_views.xml',
        'views/bill_register_views.xml',
        'views/team_charge_settlement_views.xml',
        'report/team_charge_report_views.xml',
        'views/menus.xml',
    ],
    'license': 'LGPL-3',
    'application': False,
}
