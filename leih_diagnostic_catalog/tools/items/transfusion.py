"""Transfusion Medicine.

Cross matching uses the ``transfusion`` layout, which prints the donor block,
both blood groups and the screening panel from dedicated fields on
examination.result (donor_name, bag_no, cross_match_status and so on) rather
than from components. The components here cover the screening results that
layout expects to find as result lines.
"""

from catalogue_spec import C, H, ITEM, S, T
from refs import (AC_TRANSFUSION, I_MICRO, M_AGGL, SP_BLOOD, T_EDTA,
                  TRANSFUSION)

_POSNEG = ['Negative*', 'Positive']

ITEMS = [
    ITEM('Cross Matching + Screening + Drawing', TRANSFUSION, AC_TRANSFUSION, 1500,
         xmlid='cross_matching_screening_drawing', category='pathology',
         layout='transfusion', tube=T_EDTA, sample=SP_BLOOD, method=M_AGGL,
         instrument=I_MICRO, own_tube=True, components=[
             H('COMPATIBILITY TESTING'),
             S('Cross Match (Immediate Spin)', ['Compatible*', 'Incompatible'],
               ref='Compatible'),
             S('Cross Match (37 C / AHG Phase)', ['Compatible*', 'Incompatible'],
               ref='Compatible'),
             H('MANDATORY DONOR SCREENING'),
             S('HBsAg', _POSNEG, ref='Negative'),
             S('Anti-HCV', _POSNEG, ref='Negative'),
             S('Anti-HIV 1 & 2', _POSNEG, ref='Negative'),
             S('VDRL / Syphilis', _POSNEG, ref='Negative'),
             S('Malarial Parasite', _POSNEG, ref='Negative'),
             T('Note', default='Blood issued only after all five mandatory '
                               'screening tests are non-reactive and the cross '
                               'match is compatible in both phases.'),
         ]),

    ITEM('Blood Grouping & Rh (Donor)', TRANSFUSION, AC_TRANSFUSION, 200,
         xmlid='blood_grouping_donor', category='pathology', layout='tabular',
         tube=T_EDTA, sample=SP_BLOOD, method=M_AGGL, components=[
             H('DONOR BLOOD GROUPING'),
             S('ABO Group', ['A', 'B', 'AB', 'O']),
             S('Rh (D) Factor', ['Positive*', 'Negative'], ref='Positive'),
         ]),
]
