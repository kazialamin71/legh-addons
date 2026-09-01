{
    'name': 'LEIH Bug Fixes',
    'version': '19.0.1.0.0',
    'category': 'Hidden',
    'summary': 'Small fixes found during the full-cycle functional test of the LEIH modules.',
    'description': """
- bill.register.add_discount() opens the 'discount' wizard with context key
  'pi_id', but discount.bill_no had no default reading it, so the discount
  form always opened unlinked from the bill it was raised on. Fixed by
  defaulting bill_no from context.
""",
    'author': 'Kazi Alamin',
    'license': 'LGPL-3',
    'depends': ['leih19'],
    'data': [],
    'installable': True,
    'application': False,
}
