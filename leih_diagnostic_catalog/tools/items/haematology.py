"""Haematology, including coagulation.

Coagulation draws into the light-blue citrate tube and must be filled to the
mark, so those tests carry ``own_tube=True`` - they can never share a specimen
with the EDTA work even though both are haematology.
"""

from catalogue_spec import C, H, ITEM, S, T
from refs import (AC_HAEM, HAEM, I_COAG, I_HAEM, I_MICRO, M_CE, M_COAG,
                  M_HPLC, M_IMPED, M_MANUAL, M_MICRO, SP_BLOOD, T_BLUE, T_EDTA)


def _cbc(name, rate, components, **kw):
    kw.setdefault('tube', T_EDTA)
    kw.setdefault('sample', SP_BLOOD)
    kw.setdefault('method', M_IMPED)
    kw.setdefault('instrument', I_HAEM)
    return ITEM(name, HAEM, AC_HAEM, rate, components=components, **kw)


def _coag(name, rate, components, **kw):
    kw.setdefault('tube', T_BLUE)
    kw.setdefault('sample', 'sample_plasma')
    kw.setdefault('method', M_COAG)
    kw.setdefault('instrument', I_COAG)
    kw.setdefault('own_tube', True)
    return ITEM(name, HAEM, AC_HAEM, rate, components=components, **kw)


_HB = C('Haemoglobin (Hb)', 'g/dL', 'M: 13.0 - 17.0  F: 12.0 - 15.0',
        low=12.0, high=17.0, crit_low=7.0, crit_high=20.0,
        male='13.0 - 17.0', female='12.0 - 15.0', child='11.0 - 14.0')
_HCT = C('Haematocrit (HCT / PCV)', '%', 'M: 40 - 50  F: 36 - 46',
         low=36, high=50, male='40 - 50', female='36 - 46')
_PLT = C('Platelet Count', '/cmm', '150,000 - 450,000',
         low=150000, high=450000, crit_low=50000, crit_high=1000000)
_TC = C('Total WBC Count', '/cmm', '4,000 - 11,000',
        low=4000, high=11000, crit_low=2000, crit_high=30000)

ITEMS = [
    _cbc('CBC (Complete Blood Count)', 400, [
        H('COMPLETE BLOOD COUNT'),
        _HB, _HCT,
        C('RBC Count', 'million/cmm', 'M: 4.5 - 5.9  F: 4.1 - 5.1',
          low=4.1, high=5.9, male='4.5 - 5.9', female='4.1 - 5.1'),
        C('MCV', 'fL', '80 - 100', low=80, high=100),
        C('MCH', 'pg', '27 - 33', low=27, high=33),
        C('MCHC', 'g/dL', '32 - 36', low=32, high=36),
        C('RDW-CV', '%', '11.5 - 14.5', low=11.5, high=14.5),
        _TC,
        H('DIFFERENTIAL COUNT'),
        C('Neutrophils', '%', '40 - 75', low=40, high=75),
        C('Lymphocytes', '%', '20 - 45', low=20, high=45),
        C('Monocytes', '%', '2 - 10', low=2, high=10),
        C('Eosinophils', '%', '1 - 6', low=1, high=6),
        C('Basophils', '%', '0 - 1', high=1),
        H('PLATELETS'),
        _PLT,
        C('MPV', 'fL', '7.5 - 11.5', low=7.5, high=11.5),
        H('ESR'),
        C('ESR (1st Hour)', 'mm', 'M: 0 - 15  F: 0 - 20',
          high=20, male='0 - 15', female='0 - 20'),
        T('Comment'),
    ], xmlid='cbc'),

    _cbc('Haemoglobin (Hb%)', 250, [_HB], xmlid='haemoglobin'),
    _cbc('Haematocrit (HCT)', 250, [_HCT], xmlid='haematocrit'),
    _cbc('Platelet Count', 300, [_PLT], xmlid='platelet_count'),
    _cbc('Plateletcrit (PCT)', 200, [
        C('Plateletcrit (PCT)', '%', '0.19 - 0.39', low=0.19, high=0.39),
        _PLT,
    ], xmlid='plateletcrit'),
    _cbc('TC, DC (Total & Differential Count)', 400, [
        H('TOTAL COUNT'), _TC,
        H('DIFFERENTIAL COUNT'),
        C('Neutrophils', '%', '40 - 75', low=40, high=75),
        C('Lymphocytes', '%', '20 - 45', low=20, high=45),
        C('Monocytes', '%', '2 - 10', low=2, high=10),
        C('Eosinophils', '%', '1 - 6', low=1, high=6),
        C('Basophils', '%', '0 - 1', high=1),
    ], xmlid='tc_dc'),
    _cbc('Circulating Eosinophil Count (TCE)', 300, [
        C('Absolute Eosinophil Count', '/cmm', '40 - 440', low=40, high=440),
    ], xmlid='circulating_eosinophil_count'),
    _cbc('Reticulocyte Count', 400, [
        C('Reticulocyte Count', '%', '0.5 - 2.5', low=0.5, high=2.5),
        C('Absolute Reticulocyte Count', '/cmm', '25,000 - 75,000', low=25000, high=75000),
    ], method=M_MICRO, instrument=I_MICRO),

    _cbc('Blood Film (PBF)', 400, [
        H('PERIPHERAL BLOOD FILM'),
        T('RBC Morphology', default='Normocytic normochromic'),
        T('WBC Morphology', default='Mature, no immature form seen'),
        T('Platelet Morphology', default='Adequate on smear'),
        S('Haemoparasite', ['Not Found*', 'Malarial Parasite Seen', 'Microfilaria Seen'],
          ref='Not Found'),
        T('Impression'),
    ], method=M_MICRO, instrument=I_MICRO, layout='narrative', category='pathology',
       xmlid='blood_film_pbf'),

    _cbc('Haemoglobin Electrophoresis', 1500, [
        H('HAEMOGLOBIN ELECTROPHORESIS'),
        C('HbA', '%', '96.5 - 98.5', low=96.5, high=98.5),
        C('HbA2', '%', '1.5 - 3.5', low=1.5, high=3.5),
        C('HbF', '%', '< 1.0', high=1.0),
        C('HbS', '%', 'Absent'),
        C('HbE', '%', 'Absent'),
        S('Interpretation',
          ['Normal Haemoglobin Pattern (AA)*', 'Beta Thalassaemia Trait',
           'HbE Trait', 'HbE Beta Thalassaemia', 'Sickle Cell Trait',
           'Sickle Cell Disease', 'Other - see comment'],
          ref='Normal Haemoglobin Pattern (AA)'),
        T('Comment'),
    ], method=M_HPLC, instrument='instrument_hba1c', required_time=3,
       xmlid='haemoglobin_electrophoresis'),

    # ----------------------------------------------------------- coagulation
    _coag('Prothrombin Time (PT / INR)', 500, [
        H('PROTHROMBIN TIME'),
        C('Patient PT', 'seconds', '11 - 14', low=11, high=14, crit_high=30),
        C('Control PT', 'seconds', '11 - 14'),
        C('INR', '', 'Normal: 0.8 - 1.2 | On warfarin: 2.0 - 3.0',
          low=0.8, high=1.2, crit_high=5.0),
        C('Prothrombin Index', '%', '70 - 100', low=70, high=100),
    ], xmlid='prothrombin_time'),
    _coag('APTT (Activated Partial Thromboplastin Time)', 1000, [
        C('Patient APTT', 'seconds', '25 - 35', low=25, high=35, crit_high=70),
        C('Control APTT', 'seconds', '25 - 35'),
    ], xmlid='aptt'),
    _coag('BT, CT (Bleeding & Clotting Time)', 100, [
        C('Bleeding Time (BT)', 'minutes', '2 - 7', low=2, high=7),
        C('Clotting Time (CT)', 'minutes', '4 - 9', low=4, high=9),
    ], method=M_MANUAL, instrument=None, tube=None, sample=None,
       sample_req=False, manual=True, own_tube=False, xmlid='bt_ct'),
    _coag('Fibrinogen Level', 1500, [
        C('Fibrinogen', 'mg/dL', '200 - 400', low=200, high=400, crit_low=100),
    ], xmlid='fibrinogen_level'),
    _coag('D-Dimer', 1200, [
        C('D-Dimer', 'ng/mL FEU', '< 500', high=500),
    ], method='method_clia', instrument='instrument_immunoassay', xmlid='d_dimer'),
    _coag('Fibrin Degradation Products (FDP)', 1400, [
        C('FDP', 'ug/mL', '< 5', high=5),
    ], xmlid='fdp'),
]
