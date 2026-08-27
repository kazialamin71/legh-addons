"""Named antibiotic panels.

Each entry is the list of ``lab.antibiotic`` xmlids offered to the technician
when growth is reported. Panels are specimen-specific on purpose: reporting
nitrofurantoin on a blood isolate or colistin on a routine wound swab is
clinically misleading, and the legacy export got this wrong by giving every
culture the same 36-drug list.

Order within a panel follows the drug-class sequence in
``data/06_antibiotics.xml``, so the printed antibiogram groups related agents.
"""

_L = 'leih19.'          # agents shipped by leih19
_C = ''                 # agents added by this module (local xmlids)

# Gram-negative workhorse panel - the base most specimens build on.
_GRAM_NEG = [
    _L + 'antibiotic_ampicillin',
    _L + 'antibiotic_amoxiclav',
    _L + 'antibiotic_piptaz',
    _L + 'antibiotic_cefuroxime',
    _L + 'antibiotic_ceftriaxone',
    'antibiotic_cefotaxime',
    'antibiotic_ceftazidime',
    _L + 'antibiotic_cefepime',
    _L + 'antibiotic_imipenem',
    _L + 'antibiotic_meropenem',
    _L + 'antibiotic_amikacin',
    _L + 'antibiotic_gentamicin',
    _L + 'antibiotic_ciprofloxacin',
    _L + 'antibiotic_levofloxacin',
    _L + 'antibiotic_cotrimoxazole',
]

_GRAM_POS = [
    'antibiotic_penicillin',
    _L + 'antibiotic_amoxiclav',
    'antibiotic_cloxacillin',
    'antibiotic_cefoxitin',
    _L + 'antibiotic_ceftriaxone',
    _L + 'antibiotic_gentamicin',
    _L + 'antibiotic_ciprofloxacin',
    _L + 'antibiotic_levofloxacin',
    _L + 'antibiotic_azithromycin',
    'antibiotic_erythromycin',
    'antibiotic_clindamycin',
    _L + 'antibiotic_doxycycline',
    _L + 'antibiotic_vancomycin',
    _L + 'antibiotic_linezolid',
    _L + 'antibiotic_cotrimoxazole',
]

PANELS = {
    # Urine: oral agents that concentrate in urine matter more than broad IV cover.
    'urine': _GRAM_NEG + [
        _L + 'antibiotic_nitrofurantoin',
        'antibiotic_fosfomycin',
        'antibiotic_cefixime',
        'antibiotic_mecillinam',
        'antibiotic_nalidixic_acid',
    ],

    # Blood: systemic agents only, plus the last-resort drugs an ICU will ask for.
    'blood': _GRAM_NEG + [
        'antibiotic_aztreonam',
        'antibiotic_tigecycline',
        'antibiotic_colistin',
        _L + 'antibiotic_vancomycin',
        _L + 'antibiotic_linezolid',
        'antibiotic_cefoxitin',
        'antibiotic_clindamycin',
    ],

    # Wound / pus: skin flora means staphylococcal cover is as important as GN.
    'wound': _GRAM_NEG + [
        'antibiotic_cloxacillin',
        'antibiotic_cefoxitin',
        'antibiotic_clindamycin',
        'antibiotic_erythromycin',
        _L + 'antibiotic_doxycycline',
        _L + 'antibiotic_vancomycin',
        _L + 'antibiotic_linezolid',
        'antibiotic_colistin',
    ],

    # Respiratory: atypical and pneumococcal cover.
    'respiratory': _GRAM_NEG + [
        _L + 'antibiotic_amoxicillin',
        _L + 'antibiotic_azithromycin',
        'antibiotic_erythromycin',
        _L + 'antibiotic_doxycycline',
        'antibiotic_moxifloxacin',
        _L + 'antibiotic_linezolid',
        'antibiotic_colistin',
        'antibiotic_tigecycline',
    ],

    # Stool: enteric pathogens; most systemic agents are irrelevant here.
    'stool': [
        _L + 'antibiotic_ampicillin',
        _L + 'antibiotic_amoxiclav',
        _L + 'antibiotic_ceftriaxone',
        'antibiotic_cefixime',
        _L + 'antibiotic_ciprofloxacin',
        _L + 'antibiotic_levofloxacin',
        'antibiotic_pefloxacin',
        'antibiotic_nalidixic_acid',
        _L + 'antibiotic_azithromycin',
        _L + 'antibiotic_cotrimoxazole',
        'antibiotic_chloramphenicol',
        'antibiotic_tetracycline',
        'antibiotic_furazolidone',
    ],

    # Eye: topical agents, since that is how the result will be acted on.
    'eye': [
        _L + 'antibiotic_ampicillin',
        _L + 'antibiotic_amoxiclav',
        'antibiotic_cloxacillin',
        'antibiotic_cephradine',
        'antibiotic_cephalexin',
        _L + 'antibiotic_ceftriaxone',
        'antibiotic_ceftazidime',
        _L + 'antibiotic_gentamicin',
        'antibiotic_tobramycin',
        'antibiotic_neomycin',
        _L + 'antibiotic_ciprofloxacin',
        _L + 'antibiotic_levofloxacin',
        'antibiotic_moxifloxacin',
        'antibiotic_chloramphenicol',
        'antibiotic_tetracycline',
        _L + 'antibiotic_azithromycin',
        _L + 'antibiotic_vancomycin',
    ],
}
