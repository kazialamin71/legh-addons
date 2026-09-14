{
    'name': 'LEIS Blood Bank',
    'summary': 'Transfusion medicine: donor register, cross matching, screening and the issue slip',
    'description': """
Cross Matching + Screening + Drawing is billed and reported like any other
investigation -- bill.register raises the examination.result, the technologist
enters it, it is verified and printed. This module supplies what a transfusion
report needs that a lab report does not:

* controlled vocabularies for blood group, donation type and component, so the
  slip cannot say "B pos", "B+ve" and "B Positive" for the same thing;
* the donor as a record, not a typed name, linked to the existing donor register;
* one bag number, one crossmatch;
* compatibility results and mandatory screening printed as separate sections,
  with a fit-for-issue verdict on the face of the slip.
""",
    'version': '19.0.1.0',
    'author': 'Mufti Muntasir Ahmed',
    'depends': ['leih19'],
    'data': [
        'views/blood_donar_views.xml',
        'views/examination_result_views.xml',
        'reports/transfusion_report.xml',
    ],
    'license': 'LGPL-3',
    'application': False,
}
