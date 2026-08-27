"""Biochemistry.

Reference ranges are adult values in the conventional units this lab reports
in; where a range is genuinely sex-specific it is given per sex rather than
averaged into one misleading band. ``low``/``high`` mirror the printed range so
results auto-flag; ``crit_low``/``crit_high`` are the call-the-ward thresholds.
"""

from catalogue_spec import C, H, ITEM, S, T
from refs import (AC_BIOCHEM, BIOCHEM, I_CHEM, I_GLUCO, I_HPLC, I_ISE, M_HPLC,
                  M_ISE, M_MANUAL, M_PHOTO, SP_CSF, SP_FLUID, SP_PLASMA,
                  SP_SERUM, SP_URINE, SP_URINE24, T_GOLD, T_GREEN, T_GREY,
                  T_POT, T_URINE)


def _chem(name, rate, components, **kw):
    """Serum chemistry on the main analyser - the default shape here."""
    kw.setdefault('tube', T_GOLD)
    kw.setdefault('sample', SP_SERUM)
    kw.setdefault('method', M_PHOTO)
    kw.setdefault('instrument', I_CHEM)
    return ITEM(name, BIOCHEM, AC_BIOCHEM, rate, components=components, **kw)


def _glucose(name, rate, components, **kw):
    """Glucose work draws into fluoride-oxalate, never a plain gold tube."""
    kw.setdefault('tube', T_GREY)
    kw.setdefault('sample', SP_PLASMA)
    kw.setdefault('method', M_PHOTO)
    kw.setdefault('instrument', I_CHEM)
    return ITEM(name, BIOCHEM, AC_BIOCHEM, rate, components=components, **kw)


# Reused component definitions, so a range is corrected in one place.
_GLU_FASTING = C('Fasting Blood Sugar', 'mmol/L', '3.9 - 6.1',
                 low=3.9, high=6.1, crit_low=2.8, crit_high=25.0)
_GLU_2HABF = C('Blood Sugar 2 Hours ABF', 'mmol/L', '< 7.8',
               high=7.8, crit_high=25.0)
_GLU_RANDOM = C('Random Blood Sugar', 'mmol/L', '< 11.1',
                high=11.1, crit_low=2.8, crit_high=25.0)
_CREATININE = C('Serum Creatinine', 'mg/dL', '0.6 - 1.3',
                low=0.6, high=1.3, crit_high=6.0,
                male='0.7 - 1.3', female='0.6 - 1.1', child='0.3 - 0.7')
_UREA = C('Serum Urea', 'mg/dL', '15 - 45', low=15, high=45, crit_high=200)
_TOTAL_PROTEIN = C('Total Protein', 'g/dL', '6.4 - 8.3', low=6.4, high=8.3)
_ALBUMIN = C('Serum Albumin', 'g/dL', '3.5 - 5.2', low=3.5, high=5.2)
_GLOBULIN = C('Serum Globulin', 'g/dL', '2.0 - 3.5', low=2.0, high=3.5)
_AG_RATIO = C('A / G Ratio', '', '1.1 - 2.5', low=1.1, high=2.5)
_BILI_TOTAL = C('Bilirubin (Total)', 'mg/dL', '0.2 - 1.2', low=0.2, high=1.2, crit_high=15.0)
_BILI_DIRECT = C('Bilirubin (Direct)', 'mg/dL', '0.0 - 0.3', high=0.3)
_BILI_INDIRECT = C('Bilirubin (Indirect)', 'mg/dL', '0.2 - 0.9', low=0.2, high=0.9)
_SGPT = C('ALT / SGPT', 'U/L', '< 45', high=45, male='< 45', female='< 34')
_SGOT = C('AST / SGOT', 'U/L', '< 40', high=40, male='< 40', female='< 32')
_ALP = C('Alkaline Phosphatase', 'U/L', '44 - 147', low=44, high=147,
         child='Up to 400 (higher during growth spurts)')
_GGT = C('Gamma GT', 'U/L', '8 - 61', low=8, high=61, male='8 - 61', female='5 - 36')
_SODIUM = C('Sodium (Na+)', 'mmol/L', '135 - 145', low=135, high=145,
            crit_low=120, crit_high=160)
_POTASSIUM = C('Potassium (K+)', 'mmol/L', '3.5 - 5.1', low=3.5, high=5.1,
               crit_low=2.8, crit_high=6.2)
_CHLORIDE = C('Chloride (Cl-)', 'mmol/L', '98 - 107', low=98, high=107)
_BICARB = C('Bicarbonate (HCO3-)', 'mmol/L', '22 - 29', low=22, high=29)
_IRON = C('Serum Iron', 'ug/dL', '65 - 175', low=65, high=175,
          male='65 - 175', female='50 - 170')
_TIBC = C('TIBC', 'ug/dL', '250 - 450', low=250, high=450)
_TSAT = C('Transferrin Saturation', '%', '20 - 50', low=20, high=50)
_FERRITIN = C('Serum Ferritin', 'ng/mL', '30 - 400', low=30, high=400,
              male='30 - 400', female='13 - 150')

ITEMS = [
    # ---------------------------------------------------------- renal profile
    _chem('Serum Creatinine', 500, [_CREATININE]),
    _chem('Serum Urea', 300, [_UREA], xmlid='serum_urea'),
    _chem('Blood Urea Nitrogen (BUN)', 500,
          [C('Blood Urea Nitrogen', 'mg/dL', '7 - 20', low=7, high=20, crit_high=100)]),
    _chem('Serum Uric Acid', 500,
          [C('Serum Uric Acid', 'mg/dL', '3.5 - 7.2', low=3.5, high=7.2,
             male='3.5 - 7.2', female='2.6 - 6.0')],
          xmlid='serum_uric_acid'),
    _chem('Serum eGFR', 1280, [
        _CREATININE,
        C('eGFR (CKD-EPI)', 'mL/min/1.73m2', '>= 90', low=90),
    ]),
    _chem('Creatinine Clearance (CCR)', 1000, [
        H('SPECIMEN'),
        C('24 Hour Urine Volume', 'mL'),
        H('RESULT'),
        C('Serum Creatinine', 'mg/dL', '0.6 - 1.3', low=0.6, high=1.3),
        C('Urine Creatinine', 'mg/dL'),
        C('Creatinine Clearance', 'mL/min', '90 - 140', low=90, high=140),
    ], tube=T_URINE, sample=SP_URINE24, required_time=1),
    _chem('Renal Function Test (RFT)', 4200, [
        H('RENAL FUNCTION TEST'),
        _UREA, _CREATININE,
        C('Serum Uric Acid', 'mg/dL', '3.5 - 7.2', low=3.5, high=7.2),
        _SODIUM, _POTASSIUM, _CHLORIDE, _BICARB,
        C('Serum Calcium', 'mg/dL', '8.6 - 10.2', low=8.6, high=10.2),
        C('Inorganic Phosphate', 'mg/dL', '2.5 - 4.5', low=2.5, high=4.5),
        C('Total Protein', 'g/dL', '6.4 - 8.3', low=6.4, high=8.3),
        _ALBUMIN,
    ]),

    # ------------------------------------------------------------- glycaemic
    _glucose('Fasting Blood Sugar (FBS)', 180, [H('PLASMA GLUCOSE'), _GLU_FASTING]),
    _glucose('Random Blood Sugar (RBS)', 180, [H('PLASMA GLUCOSE'), _GLU_RANDOM]),
    _glucose('Blood Sugar 2 Hours ABF', 180, [H('PLASMA GLUCOSE'), _GLU_2HABF]),
    _glucose('Blood Sugar 2 Hours After Lunch', 180, [
        H('PLASMA GLUCOSE'),
        C('Blood Sugar 2 Hours After Lunch', 'mmol/L', '< 7.8', high=7.8, crit_high=25.0),
    ]),
    _glucose('Blood Sugar Fasting & 2 Hours ABF', 300,
             [H('PLASMA GLUCOSE'), _GLU_FASTING, _GLU_2HABF]),
    _glucose('Blood Sugar 2 Hours ABF & 2 Hours After Lunch', 300, [
        H('PLASMA GLUCOSE'),
        _GLU_2HABF,
        C('Blood Sugar 2 Hours After Lunch', 'mmol/L', '< 7.8', high=7.8),
    ]),
    _glucose('Plasma Glucose', 300, [H('PLASMA GLUCOSE'), _GLU_RANDOM]),
    _glucose('RBS With Corresponding Urine', 200, [
        H('PLASMA GLUCOSE'), _GLU_RANDOM,
        H('CORRESPONDING URINE'),
        S('Urine Sugar', ['Nil*', 'Trace', '+', '++', '+++', '++++'], ref='Nil'),
    ]),
    _glucose('OGTT (Fasting)', 300, [H('ORAL GLUCOSE TOLERANCE TEST'), _GLU_FASTING]),
    _glucose('OGTT (2 Hours)', 100, [
        H('ORAL GLUCOSE TOLERANCE TEST'),
        C('2 Hours After 75g Glucose', 'mmol/L', '< 7.8', high=7.8, crit_high=25.0),
    ]),
    _glucose('OGTT (Full - Fasting, 1 Hour & 2 Hours)', 450, [
        H('ORAL GLUCOSE TOLERANCE TEST (75g)'),
        _GLU_FASTING,
        C('1 Hour After 75g Glucose', 'mmol/L', '< 10.0', high=10.0),
        C('2 Hours After 75g Glucose', 'mmol/L', '< 7.8', high=7.8, crit_high=25.0),
    ]),
    _glucose('Fasting Blood Sugar & 2 Hours After 75g Glucose', 300, [
        H('ORAL GLUCOSE TOLERANCE TEST (75g)'),
        _GLU_FASTING,
        C('2 Hours After 75g Glucose', 'mmol/L', '< 7.8', high=7.8, crit_high=25.0),
    ], lab_not_required=True),
    _glucose('FBS (Glucometer Strip)', 100, [
        C('Fasting Blood Sugar', 'mmol/L', '3.9 - 6.1', low=3.9, high=6.1, crit_low=2.8),
    ], method=M_MANUAL, instrument=I_GLUCO, manual=True),
    _glucose('RBS (Glucometer Strip)', 100, [
        C('Random Blood Sugar', 'mmol/L', '< 11.1', high=11.1, crit_low=2.8, crit_high=25.0),
    ], method=M_MANUAL, instrument=I_GLUCO, manual=True),
    _glucose('2 Hours ABF (Glucometer Strip)', 100, [
        C('Blood Sugar 2 Hours ABF', 'mmol/L', '< 7.8', high=7.8, crit_high=25.0),
    ], method=M_MANUAL, instrument=I_GLUCO, manual=True),
    ITEM('HbA1c (Glycated Haemoglobin)', BIOCHEM, AC_BIOCHEM, 1200, xmlid='hba1c',
         tube='tube_lavender', sample='sample_whole_blood',
         method=M_HPLC, instrument=I_HPLC, components=[
             C('HbA1c', '%', 'Non-diabetic: < 5.7 | Pre-diabetic: 5.7 - 6.4 | Diabetic: >= 6.5',
               low=4.0, high=5.7),
             C('Estimated Average Glucose (eAG)', 'mmol/L', 'Derived from HbA1c'),
         ]),

    # ------------------------------------------------------------ lipid work
    _chem('Lipid Profile', 1200, [
        H('LIPID PROFILE (12 HOUR FASTING)'),
        C('Serum Cholesterol (Total)', 'mg/dL', 'Desirable: < 200', high=200),
        C('Serum Triglyceride', 'mg/dL', 'Normal: < 150', high=150),
        C('HDL Cholesterol', 'mg/dL', 'M: > 40  F: > 50', low=40,
          male='> 40', female='> 50'),
        C('LDL Cholesterol', 'mg/dL', 'Optimal: < 100', high=100),
        C('VLDL Cholesterol', 'mg/dL', '< 30', high=30),
        C('Total Cholesterol / HDL Ratio', '', '< 5.0', high=5.0),
    ], required_time=1),
    _chem('Serum Cholesterol', 350,
          [C('Serum Cholesterol (Total)', 'mg/dL', 'Desirable: < 200', high=200)]),
    _chem('Serum Triglyceride', 500,
          [C('Serum Triglyceride', 'mg/dL', 'Normal: < 150', high=150)]),

    # -------------------------------------------------------------- hepatic
    _chem('Liver Function Test (LFT)', 1500, [
        H('LIVER FUNCTION TEST'),
        _BILI_TOTAL, _BILI_DIRECT, _BILI_INDIRECT,
        _SGPT, _SGOT, _ALP, _GGT,
        _TOTAL_PROTEIN, _ALBUMIN, _GLOBULIN, _AG_RATIO,
    ]),
    _chem('ALT (SGPT)', 300, [_SGPT], xmlid='alt_sgpt'),
    _chem('AST (SGOT)', 500, [_SGOT], xmlid='ast_sgot'),
    _chem('Alkaline Phosphatase (ALP)', 500, [_ALP]),
    _chem('Gamma GT (GGT)', 500, [_GGT]),
    _chem('Serum Bilirubin (Total, Direct & Indirect)', 1200,
          [H('SERUM BILIRUBIN'), _BILI_TOTAL, _BILI_DIRECT, _BILI_INDIRECT]),
    _chem('Serum Bilirubin (Total)', 600, [_BILI_TOTAL]),
    _chem('Serum Bilirubin (Direct)', 300, [_BILI_DIRECT]),
    _chem('Serum Bilirubin (Indirect)', 300, [_BILI_INDIRECT]),
    _chem('Serum Bilirubin (Direct & Indirect)', 600,
          [H('SERUM BILIRUBIN'), _BILI_DIRECT, _BILI_INDIRECT]),
    _chem('Serum Ammonia', 1400,
          [C('Serum Ammonia', 'umol/L', '15 - 45', low=15, high=45, crit_high=100)],
          tube=T_GREEN, sample=SP_PLASMA, lab_not_required=True),

    # -------------------------------------------------------- protein studies
    _chem('Total Protein', 600, [_TOTAL_PROTEIN]),
    _chem('Serum Albumin', 500, [_ALBUMIN]),
    _chem('Serum Globulin', 800, [_GLOBULIN]),
    _chem('Serum A / G Ratio', 800,
          [H('PROTEIN STUDIES'), _TOTAL_PROTEIN, _ALBUMIN, _GLOBULIN, _AG_RATIO]),
    _chem('Protein Electrophoresis', 2000, [
        H('SERUM PROTEIN ELECTROPHORESIS'),
        C('Total Protein', 'g/dL', '6.4 - 8.3', low=6.4, high=8.3),
        C('Albumin', '%', '55.8 - 66.1', low=55.8, high=66.1),
        C('Alpha-1 Globulin', '%', '2.9 - 4.9', low=2.9, high=4.9),
        C('Alpha-2 Globulin', '%', '7.1 - 11.8', low=7.1, high=11.8),
        C('Beta Globulin', '%', '8.4 - 13.1', low=8.4, high=13.1),
        C('Gamma Globulin', '%', '11.1 - 18.8', low=11.1, high=18.8),
        S('M-Band', ['Not Detected*', 'Detected'], ref='Not Detected'),
        T('Interpretation'),
    ], method='method_electrophoresis', required_time=3),

    # ------------------------------------------------------------ electrolyte
    _chem('Serum Electrolytes', 1200, [
        H('SERUM ELECTROLYTES'),
        _SODIUM, _POTASSIUM, _CHLORIDE, _BICARB,
    ], method=M_ISE, instrument=I_ISE),
    _chem('Serum Potassium', 400, [_POTASSIUM], method=M_ISE, instrument=I_ISE),
    _chem('Serum Calcium', 500,
          [C('Serum Calcium (Total)', 'mg/dL', '8.6 - 10.2', low=8.6, high=10.2,
             crit_low=6.5, crit_high=13.0)]),
    _chem('Serum Inorganic Phosphate', 1200,
          [C('Inorganic Phosphate', 'mg/dL', '2.5 - 4.5', low=2.5, high=4.5,
             child='4.0 - 7.0')]),
    _chem('Serum Magnesium', 1200,
          [C('Serum Magnesium', 'mg/dL', '1.7 - 2.4', low=1.7, high=2.4, crit_low=1.0)]),
    _chem('Serum Lactate', 1400,
          [C('Serum Lactate', 'mmol/L', '0.5 - 2.2', low=0.5, high=2.2, crit_high=4.0)],
          tube=T_GREEN, sample=SP_PLASMA),

    # ------------------------------------------------------------ iron status
    _chem('Serum Iron Profile', 4200, [
        H('IRON PROFILE'), _IRON, _TIBC, _TSAT, _FERRITIN,
    ]),
    _chem('Serum Iron', 1200, [_IRON]),
    _chem('TIBC (Total Iron Binding Capacity)', 900, [_TIBC], xmlid='tibc'),
    _chem('Transferrin Saturation (TSAT)', 1800, [H('IRON STUDIES'), _IRON, _TIBC, _TSAT]),
    _chem('Serum Ferritin', 1400, [_FERRITIN]),
    _chem('Serum Folic Acid', 1200,
          [C('Folic Acid', 'ng/mL', '3.0 - 17.0', low=3.0, high=17.0)]),

    # ------------------------------------------------------- pancreas / cardiac
    _chem('Serum Amylase', 1200,
          [C('Serum Amylase', 'U/L', '25 - 125', low=25, high=125, crit_high=500)]),
    _chem('Serum Lipase', 1200,
          [C('Serum Lipase', 'U/L', '13 - 60', low=13, high=60, crit_high=180)]),
    _chem('Troponin-I', 1000,
          [C('Troponin-I', 'ng/mL', '< 0.04', high=0.04, crit_high=0.5)]),
    _chem('CK-MB', 1200,
          [C('CK-MB', 'U/L', '< 25', high=25)]),
    _chem('CPK (Creatine Phosphokinase)', 1200,
          [C('CPK Total', 'U/L', 'M: 39 - 308  F: 26 - 192', low=26, high=308,
             male='39 - 308', female='26 - 192')]),
    _chem('LDH (Lactate Dehydrogenase)', 1400,
          [C('LDH', 'U/L', '140 - 280', low=140, high=280)], lab_not_required=True),

    # ------------------------------------------------------------ urine chem
    _chem('Urine Albumin', 400,
          [S('Urine Albumin', ['Nil*', 'Trace', '+', '++', '+++', '++++'], ref='Nil')],
          tube=T_URINE, sample=SP_URINE, instrument='instrument_urine_analyzer'),
    _chem('Urine Micro-Albumin', 1200,
          [C('Urine Micro-Albumin', 'mg/L', '< 30', high=30)],
          tube=T_URINE, sample=SP_URINE),
    _chem('Urine ACR (Albumin Creatinine Ratio)', 1200, [
        H('URINE ALBUMIN CREATININE RATIO'),
        C('Urine Albumin', 'mg/L', '< 30', high=30),
        C('Urine Creatinine', 'mg/dL'),
        C('Albumin / Creatinine Ratio', 'mg/g', 'Normal: < 30 | Microalbuminuria: 30 - 300 | Macroalbuminuria: > 300',
          high=30),
        T('Interpretation'),
    ], tube=T_URINE, sample=SP_URINE),
    _chem('Urine PCR (Protein Creatinine Ratio)', 500, [
        H('URINE PROTEIN CREATININE RATIO'),
        C('Urine Total Protein', 'mg/dL'),
        C('Urine Creatinine', 'mg/dL'),
        C('Protein / Creatinine Ratio', 'mg/g', '< 150', high=150),
    ], tube=T_URINE, sample=SP_URINE),
    _chem('Protein (Albumin) Creatinine Ratio', 800, [
        H('URINE PROTEIN / ALBUMIN CREATININE RATIO'),
        C('Urine Albumin', 'mg/L', '< 30', high=30),
        C('Urine Total Protein', 'mg/dL'),
        C('Urine Creatinine', 'mg/dL'),
        C('Protein / Creatinine Ratio', 'mg/g', '< 150', high=150),
    ], tube=T_URINE, sample=SP_URINE),
    _chem('24 Hours Urinary Total Protein', 750, [
        H('24 HOUR URINE COLLECTION'),
        C('Total Volume', 'mL'),
        C('Urine Protein Concentration', 'mg/dL'),
        C('24 Hour Total Protein', 'mg/24h', '< 150', high=150),
    ], tube=T_URINE, sample=SP_URINE24, required_time=1),
    _chem('Urinary Electrolytes', 1200, [
        H('URINARY ELECTROLYTES'),
        C('Urinary Sodium', 'mmol/L', '40 - 220 (diet dependent)'),
        C('Urinary Potassium', 'mmol/L', '25 - 125 (diet dependent)'),
        C('Urinary Chloride', 'mmol/L', '110 - 250 (diet dependent)'),
    ], tube=T_URINE, sample=SP_URINE, method=M_ISE, instrument=I_ISE),
    _chem('Urinary Osmolality', 1200,
          [C('Urinary Osmolality', 'mOsm/kg', '50 - 1200', low=50, high=1200)],
          tube=T_URINE, sample=SP_URINE),
    _chem('Serum Osmolality', 1200,
          [C('Serum Osmolality', 'mOsm/kg', '275 - 295', low=275, high=295)]),
    _chem('Urine for Ketone Bodies', 450,
          [S('Ketone Bodies', ['Absent*', 'Trace', '+', '++', '+++'], ref='Absent')],
          tube=T_URINE, sample=SP_URINE, lab_not_required=True),

    # ----------------------------------------------------------- body fluids
    _chem('Ascitic / CSF / Pleural Fluid for Biochemistry', 2000, [
        H('FLUID BIOCHEMISTRY'),
        C('Fluid Total Protein', 'g/dL'),
        C('Fluid Albumin', 'g/dL'),
        C('Fluid Glucose', 'mmol/L'),
        C('Fluid LDH', 'U/L'),
        C('Serum Albumin (paired)', 'g/dL'),
        C('SAAG (Serum-Ascites Albumin Gradient)', 'g/dL',
          '>= 1.1 suggests portal hypertension'),
        T('Interpretation'),
    ], tube=T_POT, sample=SP_FLUID),
    _chem('CSF for Protein, Glucose, TC, DC & ADA', 3500, [
        H('CEREBROSPINAL FLUID'),
        C('CSF Protein', 'mg/dL', '15 - 45', low=15, high=45),
        C('CSF Glucose', 'mmol/L', '2.2 - 3.9 (about 60% of plasma)', low=2.2, high=3.9),
        C('Total Cell Count', '/cmm', '0 - 5', high=5),
        H('DIFFERENTIAL COUNT'),
        C('Lymphocytes', '%'),
        C('Neutrophils', '%'),
        C('ADA (Adenosine Deaminase)', 'U/L', '< 10', high=10),
        T('Interpretation'),
    ], tube=T_POT, sample=SP_CSF, own_tube=True),

    # ------------------------------------------------------------------ misc
    _chem('Serum ACE (Angiotensin Converting Enzyme)', 5000,
          [C('Serum ACE', 'U/L', '8 - 52', low=8, high=52)]),
    _chem('Homocysteine', 3500,
          [C('Homocysteine', 'umol/L', '5 - 15', low=5, high=15)]),
    _chem('Homa IR (Insulin Resistance Index)', 2000, [
        H('INSULIN RESISTANCE'),
        C('Fasting Blood Sugar', 'mmol/L', '3.9 - 6.1', low=3.9, high=6.1),
        C('Fasting Insulin', 'uIU/mL', '2.6 - 24.9', low=2.6, high=24.9),
        C('HOMA-IR', '', '< 2.5 (insulin sensitive)', high=2.5),
    ]),
    _chem('Random Insulin', 1400,
          [C('Insulin (Random)', 'uIU/mL', '2.6 - 24.9', low=2.6, high=24.9)]),
    _chem('C-Peptide', 1600,
          [C('C-Peptide (Fasting)', 'ng/mL', '0.8 - 3.9', low=0.8, high=3.9)]),
]
