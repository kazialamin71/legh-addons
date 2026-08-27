{
    'name': 'LEIS Diagnostic Catalogue',
    'summary': 'Clean department hierarchy, revenue accounts and the full diagnostic '
               'item catalogue with report-ready components',
    'description': """
LEIS Diagnostic Catalogue
=========================

Rebuilds the diagnostic / service catalogue that used to live as a flat export of
``examination.entry``. That export had inconsistent department names
(``Diagonistic``, ``Radiolgy & Imaging``), 47 items with no department at all,
antibiotics stored as ordinary result components, and almost no units or
reference ranges.

This module ships the catalogue as proper master data:

* **Departments** - a two-level hierarchy (Pathology > Biochemistry, Radiology &
  Imaging > USG, ...) with the lab modality set so result access control works.
* **Revenue accounts** - one income account per department, so the GL gives a
  department-wise revenue breakdown without any extra reporting layer.
* **Items** - every catalogue item carries its service group, test category,
  report layout, revenue account and provisional rate.
* **Components** - lab tests are broken into ``examination.entry.line``
  components with unit, result type, sex/child reference ranges and critical
  thresholds, so results auto-flag High/Low and print in the right layout.
* **Antibiogram panels** - microbiology tests use the antibiotic panel instead of
  fake component lines, one panel per specimen type.
* **Narrative templates** - USG / X-Ray / Echo studies get structured report
  templates the technician loads and edits.

Rates are carried over from the legacy export as **provisional** figures and are
expected to be revised before go-live.
""",
    'version': '19.0.1.0.0',
    'author': 'Mufti Muntasir Ahmed',
    'category': 'Hospital Management',
    'depends': ['leih19', 'account'],
    'data': [
        'data/01_revenue_accounts.xml',
        'data/02_departments.xml',
        'data/03_tube_colors.xml',
        'data/04_sample_types.xml',
        'data/05_methods_instruments.xml',
        'data/06_antibiotics.xml',
        'data/07_report_templates.xml',
        'data/08_retire_leih19_samples.xml',
        'data/10_biochemistry.xml',
        'data/11_haematology.xml',
        'data/12_clinical_pathology.xml',
        'data/13_serology.xml',
        'data/14_immunology.xml',
        'data/15_hormone.xml',
        'data/16_microbiology.xml',
        'data/17_histocytopathology.xml',
        'data/18_transfusion.xml',
        'data/20_radiology.xml',
        'data/21_usg.xml',
        'data/22_cardiology.xml',
        'data/30_dental.xml',
        'data/31_ot_indoor.xml',
        'data/32_general_services.xml',
        'data/33_packages.xml',
        'data/34_consumables.xml',
    ],
    'license': 'LGPL-3',
    'application': False,
}
