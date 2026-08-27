"""Clinical Pathology - routine microscopy and physical/chemical examination.

Urine and stool routines use the ``two_column`` layout: these are qualitative
findings grouped under Physical / Chemical / Microscopic headings, and the
Test-Result-Unit-Reference grid used for biochemistry reads badly for them.

Mantoux is not defined here - leih19 already ships a fully built Mantoux test
and 08_retire_leih19_samples.xml adopts it.
"""

from catalogue_spec import C, H, ITEM, S, T
from refs import (AC_CLINPATH, CLINPATH, I_MICRO, I_URINE, M_MANUAL, M_MICRO,
                  SP_SEMEN, SP_STOOL, SP_URINE, T_POT, T_STOOL, T_URINE)


def _cp(name, rate, components, **kw):
    kw.setdefault('method', M_MICRO)
    kw.setdefault('instrument', I_MICRO)
    return ITEM(name, CLINPATH, AC_CLINPATH, rate, components=components, **kw)


ITEMS = [
    _cp('Urine R/M/E (Routine & Microscopic Examination)', 250, [
        H('PHYSICAL EXAMINATION'),
        C('Quantity', 'mL'),
        S('Colour', ['Pale Yellow*', 'Straw', 'Yellow', 'Deep Yellow', 'Amber',
                     'Reddish', 'High Coloured'], ref='Pale Yellow'),
        S('Appearance', ['Clear*', 'Slightly Hazy', 'Hazy', 'Turbid'], ref='Clear'),
        C('Specific Gravity', '', '1.005 - 1.030', low=1.005, high=1.030),
        S('Deposit / Sediment', ['Nil*', 'Scanty', 'Moderate', 'Plenty'], ref='Nil'),

        H('CHEMICAL EXAMINATION'),
        C('Reaction (pH)', '', '5.0 - 8.0', low=5.0, high=8.0),
        S('Albumin', ['Nil*', 'Trace', '+', '++', '+++', '++++'], ref='Nil'),
        S('Sugar', ['Nil*', 'Trace', '+', '++', '+++', '++++'], ref='Nil'),
        S('Ketone Bodies', ['Nil*', 'Trace', '+', '++', '+++'], ref='Nil'),
        S('Bile Salt', ['Absent*', 'Present'], ref='Absent'),
        S('Bile Pigment', ['Absent*', 'Present'], ref='Absent'),
        S('Urobilinogen', ['Normal*', 'Increased', 'Absent'], ref='Normal'),
        S('Nitrite', ['Negative*', 'Positive'], ref='Negative'),

        H('MICROSCOPIC EXAMINATION'),
        C('Pus Cells', '/HPF', '0 - 5', high=5),
        C('Red Blood Cells', '/HPF', '0 - 2', high=2),
        C('Epithelial Cells', '/HPF', '0 - 5', high=5),

        H('CASTS (/LPF)'),
        S('Hyaline Cast', ['Absent*', 'Present'], ref='Absent'),
        S('Granular Cast', ['Absent*', 'Present'], ref='Absent'),
        S('Epithelial Cast', ['Absent*', 'Present'], ref='Absent'),
        S('RBC Cast', ['Absent*', 'Present'], ref='Absent'),
        S('WBC Cast', ['Absent*', 'Present'], ref='Absent'),

        H('CRYSTALS'),
        S('Calcium Oxalate', ['Absent*', 'Few', 'Moderate', 'Plenty'], ref='Absent'),
        S('Uric Acid', ['Absent*', 'Few', 'Moderate', 'Plenty'], ref='Absent'),
        S('Amorphous Phosphate', ['Absent*', 'Few', 'Moderate', 'Plenty'], ref='Absent'),
        S('Amorphous Urates', ['Absent*', 'Few', 'Moderate', 'Plenty'], ref='Absent'),
        S('Triple Phosphate', ['Absent*', 'Few', 'Moderate', 'Plenty'], ref='Absent'),
        S('Calcium Carbonate', ['Absent*', 'Few', 'Moderate', 'Plenty'], ref='Absent'),

        H('OTHERS'),
        S('Candida / Yeast', ['Absent*', 'Present'], ref='Absent'),
        S('Bacteria', ['Absent*', 'Few', 'Moderate', 'Plenty'], ref='Absent'),
        S('Trichomonas', ['Absent*', 'Present'], ref='Absent'),
        T('Comment'),
    ], layout='two_column', tube=T_URINE, sample=SP_URINE, instrument=I_URINE,
       xmlid='urine_rme'),

    _cp('Stool R/M/E (Routine & Microscopic Examination)', 200, [
        H('PHYSICAL EXAMINATION'),
        S('Colour', ['Brown*', 'Yellowish', 'Greenish', 'Blackish', 'Clay Coloured'],
          ref='Brown'),
        S('Consistency', ['Formed*', 'Semi-formed', 'Loose', 'Watery', 'Hard'],
          ref='Formed'),
        S('Mucus', ['Absent*', 'Present'], ref='Absent'),
        S('Blood (Macroscopic)', ['Absent*', 'Present'], ref='Absent'),

        H('MICROSCOPIC EXAMINATION'),
        C('Pus Cells', '/HPF', '0 - 2', high=2),
        C('Red Blood Cells', '/HPF', 'Nil', high=0),
        S('Macrophages', ['Absent*', 'Present'], ref='Absent'),
        S('Vegetable Cells', ['Absent*', 'Few', 'Moderate', 'Plenty'], ref='Absent'),
        S('Fat Globules', ['Absent*', 'Few', 'Moderate', 'Plenty'], ref='Absent'),
        S('Starch Granules', ['Absent*', 'Present'], ref='Absent'),

        H('PARASITOLOGY'),
        S('Ova', ['Not Found*', 'Ascaris lumbricoides', 'Hookworm', 'Trichuris trichiura',
                  'Enterobius vermicularis', 'Hymenolepis nana', 'Other - see comment'],
          ref='Not Found'),
        S('Cyst', ['Not Found*', 'Entamoeba histolytica', 'Entamoeba coli',
                   'Giardia lamblia', 'Other - see comment'], ref='Not Found'),
        S('Trophozoite', ['Not Found*', 'Entamoeba histolytica', 'Giardia lamblia'],
          ref='Not Found'),
        T('Comment'),
    ], layout='two_column', tube=T_STOOL, sample=SP_STOOL, xmlid='stool_rme'),

    _cp('Stool for Occult Blood (OBT)', 300, [
        S('Occult Blood', ['Negative*', 'Positive'], ref='Negative'),
    ], tube=T_STOOL, sample=SP_STOOL, xmlid='stool_obt'),

    _cp('Stool for Reducing Substance', 350, [
        S('Reducing Substance', ['Absent*', 'Trace', '+', '++', '+++'], ref='Absent'),
        C('Stool pH', '', '6.0 - 7.5', low=6.0, high=7.5),
    ], tube=T_STOOL, sample=SP_STOOL, xmlid='stool_reducing_substance'),

    _cp('Semen Analysis', 1000, [
        H('PHYSICAL EXAMINATION'),
        C('Abstinence Period', 'days', '2 - 7 days recommended'),
        C('Volume', 'mL', '>= 1.4', low=1.4),
        S('Colour', ['Greyish White*', 'Yellowish', 'Reddish'], ref='Greyish White'),
        C('Liquefaction Time', 'minutes', '< 60', high=60),
        S('Viscosity', ['Normal*', 'Increased'], ref='Normal'),
        C('pH', '', '>= 7.2', low=7.2),

        H('MICROSCOPIC EXAMINATION'),
        C('Sperm Concentration', 'million/mL', '>= 16', low=16),
        C('Total Sperm Count', 'million/ejaculate', '>= 39', low=39),
        C('Progressive Motility', '%', '>= 30', low=30),
        C('Total Motility', '%', '>= 42', low=42),
        C('Non-motile', '%'),
        C('Normal Morphology', '%', '>= 4', low=4),
        C('Vitality (Live Sperm)', '%', '>= 54', low=54),
        C('Pus Cells', '/HPF', '< 5', high=5),
        C('Red Blood Cells', '/HPF', 'Nil', high=0),
        S('Impression', ['Normozoospermia*', 'Oligozoospermia', 'Asthenozoospermia',
                         'Teratozoospermia', 'Oligoasthenoteratozoospermia',
                         'Azoospermia', 'Other - see comment'], ref='Normozoospermia'),
        T('Comment', default='Reference values as per WHO Laboratory Manual, 6th Edition (2021).'),
    ], tube=T_POT, sample=SP_SEMEN, own_tube=True, xmlid='semen_analysis'),

    _cp('HsCRP (High Sensitivity CRP)', 600, [
        C('hs-CRP', 'mg/L',
          'Low risk: < 1.0 | Average risk: 1.0 - 3.0 | High risk: > 3.0', high=3.0),
    ], tube='tube_gold_sst', sample='sample_serum', method='method_clia',
       instrument='instrument_immunoassay', xmlid='hscrp'),

    _cp('Intraocular Pressure (IOP)', 100, [
        C('Right Eye (OD)', 'mmHg', '10 - 21', low=10, high=21, crit_high=30),
        C('Left Eye (OS)', 'mmHg', '10 - 21', low=10, high=21, crit_high=30),
    ], group='procedure', method=M_MANUAL, instrument=None, sample_req=False,
       manual=True, xmlid='intraocular_pressure'),

    _cp('Blood Pressure (BP)', 50, [
        C('Systolic', 'mmHg', '90 - 120', low=90, high=120, crit_high=180),
        C('Diastolic', 'mmHg', '60 - 80', low=60, high=80, crit_high=120),
    ], group='procedure', method=M_MANUAL, instrument=None, sample_req=False,
       manual=True, lab_not_required=True, xmlid='blood_pressure'),
]
