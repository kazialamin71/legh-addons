"""Microbiology - culture & sensitivity, staining and molecular tests.

Cultures use the ``microbiology`` layout, which prints the incubation block,
the components, the organism and the antibiogram. The antibiogram comes from
``antibiotic_ids`` (a specimen-appropriate panel from tools/panels.py), NOT from
components - that is the substantive fix over the legacy export, where each
antibiotic was a component and so could only ever hold a bare text value with
no S/I/R interpretation.

The "Growth" component gates the rest: organism, colony count and sensitivity
note only appear once the technician records growth, so a no-growth report stays
a two-line report.
"""

from catalogue_spec import C, COND, H, ITEM, S, T
from refs import (AC_MICRO, I_INCUB, I_MICRO, I_PCR, M_CULTURE, M_GRAM, M_KOH,
                  M_MICRO, M_PCR, M_ZN, MICRO, SP_BLOOD, SP_CATHETER, SP_CORNEA,
                  SP_SPUTUM, SP_STOOL, SP_SWAB, SP_URINE, T_CULTURE, T_POT,
                  T_STOOL, T_SWAB, T_URINE)

_GROWTH = ['No Growth*', 'Growth']


def _culture(name, rate, tube, sample, panel, medium, xmlid,
             extra=(), incubation=(48, 37.0), **kw):
    """A culture & sensitivity test.

    ``extra`` holds specimen-specific components (colony count for urine, Gram
    film for pus) inserted before the growth block.
    """
    components = [
        H('CULTURE REPORT'),
        S('Specimen Condition', ['Satisfactory*', 'Sub-optimal', 'Rejected'],
          ref='Satisfactory'),
    ]
    components.extend(extra)
    components.extend([
        S('Growth', _GROWTH, ref='No Growth'),
        COND(T('Organism Isolated'), on='Growth', when='Growth'),
        COND(C('Colony Count', 'CFU/mL'), on='Growth', when='Growth'),
        T('Comment', default='No growth of aerobic organism after %d hours of '
                             'incubation at %.0f C.' % (incubation[0], incubation[1])),
    ])
    return ITEM(name, MICRO, AC_MICRO, rate, xmlid=xmlid, category='microbiology',
                layout='microbiology', tube=tube, sample=sample,
                method=M_CULTURE, instrument=I_INCUB, antibiotics=panel,
                medium=medium, incubation=incubation, required_time=3,
                components=components, **kw)


def _stain(name, rate, tube, sample, method, components, xmlid, **kw):
    return ITEM(name, MICRO, AC_MICRO, rate, xmlid=xmlid, category='microbiology',
                layout='microbiology', tube=tube, sample=sample, method=method,
                instrument=I_MICRO, components=components, **kw)


ITEMS = [
    # ------------------------------------------------ culture & sensitivity
    _culture('Urine for C/S', 800, T_URINE, SP_URINE, 'urine',
             'CLED / MacConkey Agar', 'urine_cs',
             extra=[S('Pus Cells', ['0 - 5 /HPF*', '5 - 10 /HPF', '10 - 20 /HPF',
                                    'Numerous'], ref='0 - 5 /HPF')]),
    _culture('Blood for C/S', 1200, T_CULTURE, SP_BLOOD, 'blood',
             'Brain Heart Infusion Broth / Blood Agar', 'blood_cs',
             incubation=(120, 37.0), own_tube=True),
    _culture('Stool for C/S', 800, T_STOOL, SP_STOOL, 'stool',
             'MacConkey / SS Agar / Selenite F Broth', 'stool_cs'),
    _culture('Sputum for C/S', 1000, T_POT, SP_SPUTUM, 'respiratory',
             'Blood Agar / Chocolate Agar / MacConkey', 'sputum_cs',
             extra=[S('Specimen Adequacy (Bartlett)',
                      ['Acceptable*', 'Salivary - repeat advised'], ref='Acceptable')]),
    _culture('Wound Swab for C/S', 800, T_SWAB, SP_SWAB, 'wound',
             'Blood Agar / MacConkey', 'wound_swab_cs'),
    _culture('Pus for C/S', 2200, T_POT, SP_SWAB, 'wound',
             'Blood Agar / MacConkey / Thioglycollate Broth', 'pus_cs',
             extra=[T('Gram Stain Finding')]),
    _culture('Tracheal Aspirate / Swab for C/S', 1200, T_POT, SP_SPUTUM,
             'respiratory', 'Blood Agar / Chocolate Agar / MacConkey',
             'tracheal_aspirate_cs'),
    _culture('Catheter Tip for C/S', 1650, T_POT, SP_CATHETER, 'blood',
             'Blood Agar (semi-quantitative roll plate)', 'catheter_tip_cs'),
    _culture('Conjunctival Swab for C/S (Right Eye)', 400, T_SWAB, SP_SWAB, 'eye',
             'Blood Agar / Chocolate Agar', 'conjunctival_swab_cs_right'),
    _culture('Conjunctival Swab for C/S (Left Eye)', 400, T_SWAB, SP_SWAB, 'eye',
             'Blood Agar / Chocolate Agar', 'conjunctival_swab_cs_left'),
    _culture('Corneal Scraping for C/S', 250, T_SWAB, SP_CORNEA, 'eye',
             'Blood Agar / Chocolate Agar / Sabouraud Dextrose Agar',
             'corneal_scraping_cs', lab_not_required=True),

    # ---------------------------------------------------------- microscopy
    _stain('Gram Staining', 500, T_POT, SP_SWAB, M_GRAM, [
        H('GRAM STAIN'),
        S('Pus Cells', ['Nil*', 'Few', 'Moderate', 'Plenty'], ref='Nil'),
        S('Epithelial Cells', ['Nil*', 'Few', 'Moderate', 'Plenty'], ref='Nil'),
        S('Gram Positive Cocci', ['Not Seen*', 'Few', 'Moderate', 'Plenty'], ref='Not Seen'),
        S('Gram Positive Bacilli', ['Not Seen*', 'Few', 'Moderate', 'Plenty'], ref='Not Seen'),
        S('Gram Negative Cocci', ['Not Seen*', 'Few', 'Moderate', 'Plenty'], ref='Not Seen'),
        S('Gram Negative Bacilli', ['Not Seen*', 'Few', 'Moderate', 'Plenty'], ref='Not Seen'),
        S('Yeast Cells', ['Not Seen*', 'Present'], ref='Not Seen'),
        T('Comment'),
    ], 'gram_staining'),

    _stain('Sputum for Gram Staining', 750, T_POT, SP_SPUTUM, M_GRAM, [
        H('GRAM STAIN'),
        S('Specimen Adequacy (Bartlett)',
          ['Acceptable*', 'Salivary - repeat advised'], ref='Acceptable'),
        S('Pus Cells', ['Nil*', 'Few', 'Moderate', 'Plenty'], ref='Nil'),
        S('Gram Positive Cocci', ['Not Seen*', 'Few', 'Moderate', 'Plenty'], ref='Not Seen'),
        S('Gram Positive Bacilli', ['Not Seen*', 'Few', 'Moderate', 'Plenty'], ref='Not Seen'),
        S('Gram Negative Cocci', ['Not Seen*', 'Few', 'Moderate', 'Plenty'], ref='Not Seen'),
        S('Gram Negative Bacilli', ['Not Seen*', 'Few', 'Moderate', 'Plenty'], ref='Not Seen'),
        T('Comment'),
    ], 'sputum_gram_staining'),

    _stain('AFB (Acid Fast Bacilli) Staining', 600, T_POT, SP_SPUTUM, M_ZN, [
        H('ZIEHL-NEELSEN STAIN'),
        S('AFB', ['Not Found*', 'Scanty (1-9/100 fields)', '1+', '2+', '3+'],
          ref='Not Found'),
        T('Comment', default='No acid fast bacilli seen in the smear examined. '
                             'A single negative smear does not exclude tuberculosis.'),
    ], 'afb_staining'),

    _stain('Corneal Scraping for KOH (Right Eye)', 500, T_SWAB, SP_CORNEA, M_KOH, [
        S('Fungal Filaments', ['Not Seen*', 'Seen'], ref='Not Seen'),
        S('Yeast Cells', ['Not Seen*', 'Seen'], ref='Not Seen'),
        T('Comment'),
    ], 'corneal_scraping_koh_right'),
    _stain('Corneal Scraping for KOH (Left Eye)', 500, T_SWAB, SP_CORNEA, M_KOH, [
        S('Fungal Filaments', ['Not Seen*', 'Seen'], ref='Not Seen'),
        S('Yeast Cells', ['Not Seen*', 'Seen'], ref='Not Seen'),
        T('Comment'),
    ], 'corneal_scraping_koh_left'),

    # ---------------------------------------------------------- molecular
    ITEM('GeneXpert MTB/RIF', MICRO, AC_MICRO, 6500, xmlid='genexpert_mtb_rif',
         category='microbiology', layout='special', tube=T_POT, sample=SP_SPUTUM,
         method=M_PCR, instrument=I_PCR, required_time=1, components=[
             H('GENEXPERT MTB/RIF ASSAY'),
             S('M. tuberculosis complex',
               ['Not Detected*', 'Detected (Very Low)', 'Detected (Low)',
                'Detected (Medium)', 'Detected (High)'], ref='Not Detected'),
             # Not gated on the MTB line: rifampicin resistance is reported
             # whenever MTB is detected at any level, and COND can only key off
             # a single trigger value.
             S('Rifampicin Resistance',
               ['Not Applicable*', 'Not Detected', 'Detected', 'Indeterminate'],
               ref='Not Applicable'),
             T('Comment'),
         ]),

    ITEM('RT-PCR for COVID-19 (SARS-CoV-2)', MICRO, AC_MICRO, 3500,
         xmlid='rt_pcr_covid19', category='microbiology', layout='special',
         tube=T_SWAB, sample=SP_SWAB, method=M_PCR, instrument=I_PCR,
         required_time=1, components=[
             H('SARS-CoV-2 REAL-TIME RT-PCR'),
             S('Result', ['Not Detected*', 'Detected', 'Inconclusive'], ref='Not Detected'),
             COND(C('Ct Value (E gene)', ''), on='Result', when='Detected'),
             COND(C('Ct Value (RdRp / ORF1ab)', ''), on='Result', when='Detected'),
             T('Comment'),
         ]),

    ITEM('PCR for Zika, Dengue & Chikungunya Virus', MICRO, AC_MICRO, 6500,
         xmlid='pcr_zika_dengue_chikungunya', category='microbiology',
         layout='special', tube='tube_gold_sst', sample='sample_serum',
         method=M_PCR, instrument=I_PCR, required_time=3, components=[
             H('ARBOVIRUS MULTIPLEX RT-PCR'),
             S('Zika Virus RNA', ['Not Detected*', 'Detected'], ref='Not Detected'),
             S('Dengue Virus RNA', ['Not Detected*', 'Detected'], ref='Not Detected'),
             S('Chikungunya Virus RNA', ['Not Detected*', 'Detected'], ref='Not Detected'),
             T('Comment'),
         ]),

    ITEM('Urine for Toxicology Screen', MICRO, AC_MICRO, 5000,
         xmlid='urine_toxicology_screen', category='microbiology', layout='special',
         tube=T_URINE, sample=SP_URINE, method='method_ict', components=[
             H('DRUGS OF ABUSE SCREEN'),
             S('Amphetamine', ['Negative*', 'Positive'], ref='Negative'),
             S('Benzodiazepines', ['Negative*', 'Positive'], ref='Negative'),
             S('Cannabinoids (THC)', ['Negative*', 'Positive'], ref='Negative'),
             S('Opiates', ['Negative*', 'Positive'], ref='Negative'),
             S('Cocaine', ['Negative*', 'Positive'], ref='Negative'),
             T('Comment', default='Screening result only. A positive screen must be '
                                  'confirmed by a quantitative method before it is '
                                  'used for any clinical or legal purpose.'),
         ]),

    # Individually billable drug-of-abuse screens. They duplicate analytes in
    # the full panel above on purpose: outpatients are commonly billed for one.
    ITEM('Amphetamine (Urine Screen)', MICRO, AC_MICRO, 1400,
         xmlid='amphetamine_urine', category='microbiology', layout='tabular',
         tube=T_URINE, sample=SP_URINE, method='method_ict', components=[
             S('Amphetamine', ['Negative*', 'Positive'], ref='Negative'),
         ]),
    ITEM('Benzodiazepines (Urine Screen)', MICRO, AC_MICRO, 1400,
         xmlid='benzodiazepines_urine', category='microbiology', layout='tabular',
         tube=T_URINE, sample=SP_URINE, method='method_ict', components=[
             S('Benzodiazepines', ['Negative*', 'Positive'], ref='Negative'),
         ]),
    ITEM('Cannabinoids (Urine Screen)', MICRO, AC_MICRO, 1400,
         xmlid='cannabinoids_urine', category='microbiology', layout='tabular',
         tube=T_URINE, sample=SP_URINE, method='method_ict', components=[
             S('Cannabinoids (THC)', ['Negative*', 'Positive'], ref='Negative'),
         ]),
    ITEM('Opiates (Urine Screen)', MICRO, AC_MICRO, 1400,
         xmlid='opiates_urine', category='microbiology', layout='tabular',
         tube=T_URINE, sample=SP_URINE, method='method_ict', components=[
             S('Opiates', ['Negative*', 'Positive'], ref='Negative'),
         ]),
]
