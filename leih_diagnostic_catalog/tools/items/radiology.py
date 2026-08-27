"""Radiology - X-Ray, CT and MRI.

Only the studies the legacy catalogue actually carried are seeded here. Plain
film and cross-sectional studies are added as the hospital's imaging list grows;
the department, revenue account and narrative layout are already in place for
them.
"""

from catalogue_spec import C, H, ITEM, T
from refs import AC_MRI, AC_XRAY, MRI, XRAY

ITEMS = [
    ITEM('Bone Mineral Density (BMD / DEXA)', XRAY, AC_XRAY, 3000, xmlid='bmd',
         category='radiology', layout='narrative', sample_req=False,
         lab_not_required=True, templates=['tpl_bmd'], components=[
             H('DEXA SUMMARY'),
             C('Lumbar Spine T-Score', ''),
             C('Femoral Neck T-Score', ''),
             C('Total Hip T-Score', ''),
             T('WHO Classification'),
         ]),

    ITEM('MRA of Neck Vessels', MRI, AC_MRI, 7000, xmlid='mra_neck_vessels',
         category='radiology', layout='narrative', sample_req=False,
         lab_not_required=True, required_time=1, templates=['tpl_mra_neck']),
]
