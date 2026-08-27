"""Serology - rapid tests, agglutination and titres.

Almost everything here is qualitative, so components are selection type with a
default of the negative/normal answer. That default is what makes result entry
fast: the technician only touches the ones that are positive.
"""

from catalogue_spec import C, H, ITEM, S, T
from refs import (AC_SEROLOGY, I_MICRO, M_AGGL, M_ELISA, M_ICT, M_MICRO,
                  SEROLOGY, SP_BLOOD, SP_SERUM, SP_STOOL, T_EDTA, T_GOLD,
                  T_STOOL)

_POSNEG = ['Negative*', 'Positive']
_TITRE = ['1:20', '1:40', '1:80', '1:160', '1:320', '1:640']


def _ict(name, rate, components, **kw):
    kw.setdefault('tube', T_GOLD)
    kw.setdefault('sample', SP_SERUM)
    kw.setdefault('method', M_ICT)
    return ITEM(name, SEROLOGY, AC_SEROLOGY, rate, components=components, **kw)


def _rapid(name, rate, analyte, **kw):
    """The common shape: one qualitative analyte, negative by default."""
    return _ict(name, rate, [S(analyte, _POSNEG, ref='Negative')], **kw)


ITEMS = [
    _ict('Widal Test', 600, [
        H('WIDAL TEST (TUBE AGGLUTINATION)'),
        S('S. typhi "O" (TO)', ['Not Detected*'] + _TITRE, ref='< 1:80'),
        S('S. typhi "H" (TH)', ['Not Detected*'] + _TITRE, ref='< 1:80'),
        S('S. paratyphi "AH"', ['Not Detected*'] + _TITRE, ref='< 1:80'),
        S('S. paratyphi "BH"', ['Not Detected*'] + _TITRE, ref='< 1:80'),
        T('Comment', default='A single raised titre is suggestive only; a four-fold '
                             'rise in paired sera taken 7-10 days apart is diagnostic.'),
    ], method=M_AGGL, xmlid='widal_test'),

    _ict('Febrile Antigen Test', 1200, [
        H('FEBRILE ANTIGEN PROFILE'),
        S('S. typhi "O"', ['Not Detected*'] + _TITRE, ref='< 1:80'),
        S('S. typhi "H"', ['Not Detected*'] + _TITRE, ref='< 1:80'),
        S('S. paratyphi "AH"', ['Not Detected*'] + _TITRE, ref='< 1:80'),
        S('S. paratyphi "BH"', ['Not Detected*'] + _TITRE, ref='< 1:80'),
        S('Brucella abortus', ['Not Detected*'] + _TITRE, ref='< 1:80'),
        S('Brucella melitensis', ['Not Detected*'] + _TITRE, ref='< 1:80'),
        S('Proteus OX-19 (Weil-Felix)', ['Not Detected*'] + _TITRE, ref='< 1:80'),
        T('Comment'),
    ], method=M_AGGL, xmlid='febrile_antigen'),

    _ict('Triple Antigen Test', 1000, [
        H('TRIPLE ANTIGEN'),
        S('S. typhi "O"', ['Not Detected*'] + _TITRE, ref='< 1:80'),
        S('S. typhi "H"', ['Not Detected*'] + _TITRE, ref='< 1:80'),
        S('S. paratyphi "AH"', ['Not Detected*'] + _TITRE, ref='< 1:80'),
        T('Comment'),
    ], method=M_AGGL, xmlid='triple_antigen'),

    ITEM('Blood Group & Rh Typing', SEROLOGY, AC_SEROLOGY, 200,
         tube=T_EDTA, sample=SP_BLOOD, method=M_AGGL, xmlid='blood_group',
         components=[
             H('BLOOD GROUPING'),
             S('ABO Group', ['A', 'B', 'AB', 'O']),
             S('Rh (D) Factor', ['Positive*', 'Negative'], ref='Positive'),
         ]),

    _rapid('HBsAg (Screening - ICT)', 300, 'HBsAg', xmlid='hbsag_screening'),
    _rapid('HBsAg (ELISA)', 600, 'HBsAg', method=M_ELISA, xmlid='hbsag_elisa'),
    _rapid('Anti-HCV (Screening - ICT)', 300, 'Anti-HCV', xmlid='anti_hcv_screening'),
    _rapid('HIV 1 & 2 (Screening - ICT)', 300, 'Anti-HIV 1 & 2', xmlid='hiv_screening'),
    _rapid('Anti-HIV (ELISA)', 2000, 'Anti-HIV 1 & 2', method=M_ELISA, xmlid='anti_hiv_elisa'),
    _rapid('VDRL', 600, 'VDRL', method=M_AGGL, xmlid='vdrl'),
    _rapid('TPHA (Screening Test)', 700, 'TPHA', method=M_AGGL,
           lab_not_required=True, xmlid='tpha'),
    _rapid('Pregnancy Test (Urine hCG)', 300, 'Urine hCG',
           tube='tube_urine_container', sample='sample_urine', xmlid='pregnancy_test'),

    _ict('Dengue NS1 Antigen (ICT)', 300, [
        S('Dengue NS1 Antigen', _POSNEG, ref='Negative'),
    ], xmlid='dengue_ns1'),
    _ict('Dengue IgM', 300, [
        S('Dengue IgM', _POSNEG, ref='Negative'),
    ], xmlid='dengue_igm'),
    _ict('Dengue IgG & IgM', 300, [
        H('DENGUE ANTIBODY'),
        S('Dengue IgM', _POSNEG, ref='Negative'),
        S('Dengue IgG', _POSNEG, ref='Negative'),
    ], xmlid='dengue_igg_igm'),
    _ict('Chikungunya IgG & IgM', 1500, [
        H('CHIKUNGUNYA ANTIBODY'),
        S('Chikungunya IgM', _POSNEG, ref='Negative'),
        S('Chikungunya IgG', _POSNEG, ref='Negative'),
    ], xmlid='chikungunya_igg_igm'),

    _ict('Malaria Parasite (MP)', 300, [
        S('Malarial Parasite', ['Not Found*', 'P. falciparum', 'P. vivax',
                                'P. malariae', 'P. ovale', 'Mixed Infection'],
          ref='Not Found'),
        C('Parasite Density', '/uL'),
        T('Comment'),
    ], tube=T_EDTA, sample=SP_BLOOD, method=M_MICRO, instrument=I_MICRO,
       xmlid='malaria_parasite'),
    _ict('ICT for Malaria', 1200, [
        H('MALARIA RAPID ANTIGEN'),
        S('P. falciparum (HRP-2)', _POSNEG, ref='Negative'),
        S('Pan-malarial (pLDH)', _POSNEG, ref='Negative'),
    ], tube=T_EDTA, sample=SP_BLOOD, lab_not_required=True, xmlid='ict_malaria'),

    _rapid('Rubella IgG', 1200, 'Rubella IgG', method=M_ELISA, xmlid='rubella_igg'),
    _rapid('Rubella IgM', 1200, 'Rubella IgM', method=M_ELISA, xmlid='rubella_igm'),

    _ict('Anti H. pylori IgG', 1200, [
        S('Anti H. pylori IgG', _POSNEG, ref='Negative'),
    ], method=M_ELISA, xmlid='anti_h_pylori_igg'),
    _ict('H. pylori Stool Antigen', 1200, [
        S('H. pylori Antigen', _POSNEG, ref='Negative'),
    ], tube=T_STOOL, sample=SP_STOOL, xmlid='h_pylori_stool_antigen'),

    _ict('CRP (C-Reactive Protein)', 600, [
        C('CRP', 'mg/L', '< 6', high=6),
    ], method=M_AGGL, xmlid='crp'),
    _ict('ASO Titre', 600, [
        C('ASO Titre', 'IU/mL', '< 200', high=200),
    ], method=M_AGGL, lab_not_required=True, xmlid='aso_titre'),
    _ict('RA Test (Qualitative)', 500, [
        S('Rheumatoid Factor', _POSNEG, ref='Negative'),
    ], method=M_AGGL, xmlid='ra_test_qualitative'),

    _ict("Coombs Test (Direct & Indirect)", 300, [
        H('ANTIGLOBULIN TEST'),
        S('Direct Coombs Test (DCT)', _POSNEG, ref='Negative'),
        S('Indirect Coombs Test (ICT)', _POSNEG, ref='Negative'),
    ], tube=T_EDTA, sample=SP_BLOOD, method=M_AGGL, xmlid='coombs_test'),
    _ict('Rh Antibody Titre', 1200, [
        S('Rh Antibody', ['Not Detected*'] + _TITRE, ref='Not Detected'),
        T('Comment'),
    ], tube=T_EDTA, sample=SP_BLOOD, method=M_AGGL, xmlid='rh_antibody_titre'),
]
