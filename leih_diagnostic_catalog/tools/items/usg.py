"""Ultrasonography.

All narrative layout - a sonographic report is prose plus measurements. Each
study carries the templates a sonologist would reasonably load for it, and
nothing needs a specimen, so `sample_req` is False throughout and no tube
colour is set (these never reach the phlebotomy sticker queue).
"""

from catalogue_spec import ITEM
from refs import AC_USG, USG

_WA = 'tpl_usg_whole_abdomen'
_UPPER = 'tpl_usg_upper_abdomen'
_KUB = 'tpl_usg_kub_prostate'
_PELVIS = 'tpl_usg_pelvis'
_PREG = 'tpl_usg_pregnancy_profile'
_ANOM = 'tpl_usg_anomaly_scan'
_BPP = 'tpl_usg_biophysical_profile'
_THYROID = 'tpl_usg_thyroid_neck'
_BREAST = 'tpl_usg_breast'
_BRAIN = 'tpl_usg_brain'
_GENERIC = 'tpl_usg_generic'


def _usg(name, rate, templates, xmlid, **kw):
    return ITEM(name, USG, AC_USG, rate, xmlid=xmlid, category='descriptive',
                layout='narrative', sample_req=False, templates=templates, **kw)


ITEMS = [
    _usg('USG of Whole Abdomen (2D)', 1500, [_WA, _GENERIC], 'usg_whole_abdomen',
         lab_not_required=True),
    _usg('USG of Whole Abdomen with MCC & PVR', 1800, [_WA, _KUB, _GENERIC],
         'usg_whole_abdomen_mcc_pvr', lab_not_required=True),
    _usg('USG of Upper Abdomen / HBS', 1200, [_UPPER, _GENERIC], 'usg_upper_abdomen'),
    _usg('USG of HBS', 250, [_UPPER, _GENERIC], 'usg_hbs'),
    _usg('USG of Lower Abdomen', 1200, [_PELVIS, _KUB, _GENERIC], 'usg_lower_abdomen'),
    _usg('USG of Pelvis', 1200, [_PELVIS, _GENERIC], 'usg_pelvis', lab_not_required=True),
    _usg('USG - Trans Vaginal (TVS)', 1500, [_PELVIS, _GENERIC], 'usg_tvs'),
    _usg('USG of KUB Region', 1500, [_KUB, _GENERIC], 'usg_kub_region',
         lab_not_required=True),
    _usg('USG of KUB, Prostate & PVR', 1500, [_KUB, _GENERIC], 'usg_kub_prostate_pvr'),
    _usg('USG of KUB, Prostate, PVR & MCC', 1800, [_KUB, _GENERIC],
         'usg_kub_prostate_pvr_mcc'),
    _usg('USG of Pregnancy Profile', 1200, [_PREG, _GENERIC], 'usg_pregnancy_profile',
         lab_not_required=True),
    _usg('USG Anomaly Scan', 2500, [_ANOM, _PREG, _GENERIC], 'usg_anomaly_scan',
         lab_not_required=True),
    _usg('Biophysical Profile', 1500, [_BPP, _PREG, _GENERIC], 'usg_biophysical_profile',
         lab_not_required=True),
    _usg('USG of Pregnancy Biophysical Profile', 1800, [_BPP, _PREG, _GENERIC],
         'usg_pregnancy_biophysical_profile'),
    _usg('USG of Thyroid (2D)', 1500, [_THYROID, _GENERIC], 'usg_thyroid',
         lab_not_required=True),
    _usg('USG of Neck', 1500, [_THYROID, _GENERIC], 'usg_neck'),
    _usg('USG of Single Breast', 1500, [_BREAST, _GENERIC], 'usg_single_breast'),
    _usg('USG of Both Breasts', 2000, [_BREAST, _GENERIC], 'usg_both_breasts'),
    _usg('USG of Both Axillary Regions', 1500, [_BREAST, _GENERIC],
         'usg_both_axillary_regions', lab_not_required=True),
    _usg('USG of Brain', 2500, [_BRAIN, _GENERIC], 'usg_brain', lab_not_required=True),
    _usg('Ultrasonogram (4D USG)', 2000, [_PREG, _ANOM, _GENERIC], 'usg_4d'),
    _usg('Portable USG (Bedside)', 2500, [_GENERIC], 'usg_portable',
         lab_not_required=True, indoor=True),
]
