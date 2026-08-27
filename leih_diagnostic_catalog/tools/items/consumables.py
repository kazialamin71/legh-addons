"""Consumables and disposables billed alongside a test or procedure.

These are the items leih19's `support_item_ids` is designed to attach
automatically - a vacuette disposable added whenever blood is drawn, for
instance. They are catalogued here first so that wiring has something to point
at.
"""

from catalogue_spec import ITEM
from refs import AC_CONSUMABLE, CONSUMABLE


def _cons(name, rate, xmlid, **kw):
    return ITEM(name, CONSUMABLE, AC_CONSUMABLE, rate, xmlid=xmlid,
                group='consumable', sample_req=False, **kw)


ITEMS = [
    _cons('Needle for Vacuette (1 Unit)', 20, 'cons_needle_vacuette'),
    _cons('Disposable for Vacuette', 10, 'cons_disposable_vacuette', manual=True,
          lab_not_required=True),
    _cons('Disposable for Vacuette (1 Unit)', 20, 'cons_disposable_vacuette_1',
          manual=True, lab_not_required=True),
    _cons('Disposable for Vacuette (2 Units)', 40, 'cons_disposable_vacuette_2'),
    _cons('Disposable for Vacuette (3 Units)', 60, 'cons_disposable_vacuette_3',
          manual=True, lab_not_required=True),
    _cons('Blood Bag Set', 400, 'cons_blood_bag_set'),
    _cons('75g Glucose (Oral Load)', 300, 'cons_glucose_75g'),
]
