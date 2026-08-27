"""Dental procedures.

Pure service charges: no specimen, no lab result, so `service_group='dental'`
and `sample_req=False`. leih19 only generates an examination.result for
diagnostic items, so these bill and print on the money receipt without ever
appearing in a technician's result queue.

The two dental radiographs are the exception - they are diagnostic imaging and
carry a narrative layout so a finding can be recorded.
"""

from catalogue_spec import ITEM
from refs import AC_DENTAL, DENTAL


def _d(name, rate, xmlid, **kw):
    kw.setdefault('lab_not_required', True)
    return ITEM(name, DENTAL, AC_DENTAL, rate, xmlid=xmlid, group='dental',
                sample_req=False, **kw)


ITEMS = [
    # ------------------------------------------------- scaling & prophylaxis
    _d('Normal Scaling', 1200, 'dental_normal_scaling'),
    _d('Scaling with Polishing (SP)', 1500, 'dental_scaling_polishing'),
    _d('Scaling & Polishing with Curettage and Deep Curettage', 2500,
       'dental_scaling_curettage', lab_not_required=False),

    # -------------------------------------------------------------- fillings
    _d('Treatment Filling (TF)', 300, 'dental_treatment_filling'),
    _d('Light Cure Filling Type-1 (LCF)', 1200, 'dental_lcf_type1'),
    _d('Light Cure Filling Type-2 (LCF)', 1500, 'dental_lcf_type2'),
    _d('Light Cure Filling Type-3 (LCF)', 2000, 'dental_lcf_type3'),
    _d('Tooth Colour Filling (Glass Ionomer)', 800, 'dental_tooth_colour_gi'),
    _d('Permanent Teeth - Glass Ionomer Filling', 1500, 'dental_permanent_gi_filling'),
    _d('Dental Dressing', 300, 'dental_dressing'),

    # --------------------------------------------------- root canal therapy
    _d('RCT (Anterior)', 2500, 'dental_rct_anterior'),
    _d('RCT (Posterior)', 3000, 'dental_rct_posterior'),
    _d('Re-RCT', 7000, 'dental_re_rct'),
    _d('RCT Anterior - Each Visit', 500, 'dental_rct_ant_each_visit'),
    _d('RCT Anterior - 2nd Visit', 1000, 'dental_rct_ant_2nd_visit'),
    _d('RCT Anterior - 4th Visit', 2000, 'dental_rct_ant_4th_visit'),
    _d('RCT (Endo Motor) - Each Visit', 500, 'dental_rct_endo_each_visit'),
    _d('RCT (Endo Motor) - Visit 1', 1000, 'dental_rct_endo_visit1'),
    _d('RCT (Endo Motor) - Visit 2', 2000, 'dental_rct_endo_visit2'),
    _d('RCT (Endo Motor) - Visit 4', 4000, 'dental_rct_endo_visit4'),
    _d('RCT (Endo Motor) - Complete Treatment', 4000, 'dental_rct_endo_complete'),
    _d('RCT with Infection', 6500, 'dental_rct_infection'),
    _d('Pulpectomy', 3000, 'dental_pulpectomy'),
    _d('Pulpotomy', 2500, 'dental_pulpotomy'),
    _d('Apicectomy - 2 Teeth', 3500, 'dental_apicectomy_2', lab_not_required=False),
    _d('Apicectomy - 4 Teeth', 7000, 'dental_apicectomy_4', lab_not_required=False),

    # ------------------------------------------------------------ extraction
    _d('Milk Teeth Extraction', 500, 'dental_milk_teeth_extraction'),
    _d('Permanent Teeth Extraction (Anterior) - Simple', 2000,
       'dental_extraction_anterior_simple'),
    _d('Permanent Teeth Extraction (Posterior) - Simple', 3000,
       'dental_extraction_posterior_simple'),
    _d('Surgical Extraction - Upper', 3500, 'dental_surgical_extraction_upper'),
    _d('Surgical Extraction - Lower', 6000, 'dental_surgical_extraction_lower'),
    _d('Surgical Extraction - Lower Mesio-Angular', 7000,
       'dental_surgical_extraction_mesioangular'),
    _d('Surgical Extraction - Horizontal / Angular / Vertical', 7000,
       'dental_surgical_extraction_hav'),

    # -------------------------------------------------- prosthetics & crowns
    _d('Cap Visit', 1000, 'dental_cap_visit'),
    _d('Cast Post & Crown (Each Unit)', 7000, 'dental_cast_post_crown'),
    _d('Porcelain Cap (1 Unit)', 4500, 'dental_porcelain_cap'),
    _d('Zirconia Crown', 20000, 'dental_zirconia_crown', lab_not_required=False),
    _d('Partial Denture (Per Unit)', 1000, 'dental_partial_denture'),
    _d('Complete Denture (Upper)', 12000, 'dental_complete_denture_upper',
       lab_not_required=False),
    _d('Complete Denture (Lower)', 12000, 'dental_complete_denture_lower',
       lab_not_required=False),
    _d('Complete Denture (Upper & Lower)', 24000, 'dental_complete_denture_both',
       lab_not_required=False),

    # ---------------------------------------------------------------- surgery
    _d('Gingivectomy (Per Tooth)', 1500, 'dental_gingivectomy', lab_not_required=False),

    # ------------------------------------------------------------- radiology
    ITEM('Dental X-Ray (IOPA)', DENTAL, AC_DENTAL, 200, xmlid='dental_xray',
         category='radiology', layout='narrative', sample_req=False,
         lab_not_required=True),
    ITEM('RVG Dental X-Ray', DENTAL, AC_DENTAL, 300, xmlid='dental_rvg_xray',
         category='radiology', layout='narrative', sample_req=False),
]
