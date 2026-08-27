"""Nursing, emergency, dialysis and other general hospital services."""

from catalogue_spec import ITEM
from refs import (AC_DIALYSIS, AC_EMERGENCY, AC_NURSING, AC_OTHER, DIALYSIS,
                  EMERGENCY, NURSING)


def _svc(name, rate, xmlid, **kw):
    kw.setdefault('group', 'procedure')
    return ITEM(name, NURSING, AC_NURSING, rate, xmlid=xmlid, sample_req=False, **kw)


ITEMS = [
    # ---------------------------------------------------------- nursing care
    _svc('Injection Pushing', 300, 'svc_injection_pushing'),
    _svc('Dressing (Minor)', 300, 'svc_dressing_minor'),
    _svc('Dressing (Intermediate)', 200, 'svc_dressing_intermediate'),
    _svc('Dressing (Major)', 1000, 'svc_dressing_major'),
    _svc('IV Cannula Insertion', 0, 'svc_iv_cannula', manual=True, group='consumable'),
    _svc('Photo Therapy (Per Hour)', 200, 'svc_photo_therapy', indoor=True),
    _svc('Oxygen (Above 5 Litre)', 250, 'svc_oxygen_above_5l', group='oxygen',
         lab_not_required=True, indoor=True),

    # ------------------------------------------------------------- emergency
    ITEM('EMO Charge (Emergency Medical Officer)', EMERGENCY, AC_EMERGENCY, 300,
         xmlid='svc_emo_charge', group='consultation', sample_req=False),
    ITEM('Emergency Observation', EMERGENCY, AC_EMERGENCY, 200,
         xmlid='svc_emergency_observation', group='procedure', sample_req=False),

    # -------------------------------------------------------------- dialysis
    ITEM('Haemodialysis Charge', DIALYSIS, AC_DIALYSIS, 3000,
         xmlid='svc_haemodialysis', group='procedure', sample_req=False,
         manual=True, lab_not_required=True, indoor=True),
    ITEM('Haemodialysis Charge (Reuse Dialyser)', DIALYSIS, AC_DIALYSIS, 2500,
         xmlid='svc_haemodialysis_reuse', group='procedure', sample_req=False,
         manual=True, lab_not_required=True, indoor=True),

    # ------------------------------------------------------- administrative
    ITEM('Birth Certificate Fee', NURSING, AC_OTHER, 1000,
         xmlid='svc_birth_certificate_fee', group='other', sample_req=False),
    ITEM('Investigation Charge (Miscellaneous)', NURSING, AC_OTHER, 0,
         xmlid='svc_investigation_charge', group='other', sample_req=False,
         manual=True),
]
