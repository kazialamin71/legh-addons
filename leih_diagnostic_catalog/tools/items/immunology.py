"""Immunology - immunoassays, autoantibodies and tumour markers.

Tumour marker ranges are assay-dependent; the values here are the common CLIA
cut-offs and must be re-checked against the kit insert when the analyser or
reagent lot changes. That is exactly why they live on the catalogue component
rather than being typed into each report.
"""

from catalogue_spec import C, H, ITEM, S, T
from refs import (AC_IMMUNO, I_IMM, IMMUNO, M_CLIA, M_ELISA, M_ICT, SP_SERUM,
                  T_GOLD)

_POSNEG = ['Negative*', 'Positive']
_POSNEGEQ = ['Negative*', 'Equivocal', 'Positive']


def _imm(name, rate, components, **kw):
    kw.setdefault('tube', T_GOLD)
    kw.setdefault('sample', SP_SERUM)
    kw.setdefault('method', M_CLIA)
    kw.setdefault('instrument', I_IMM)
    return ITEM(name, IMMUNO, AC_IMMUNO, rate, components=components, **kw)


def _marker(name, rate, analyte, uom, ref, low=None, high=None, **kw):
    """One quantitative analyte - the shape most of this department takes."""
    return _imm(name, rate, [C(analyte, uom, ref, low=low, high=high)], **kw)


def _ab(name, rate, analyte, values=None, **kw):
    """One qualitative antibody result."""
    return _imm(name, rate, [S(analyte, values or _POSNEGEQ, ref='Negative')],
                method=kw.pop('method', M_ELISA), **kw)


ITEMS = [
    # ------------------------------------------------------ hepatitis panel
    _imm('HBsAg (Quantitative)', 1200, [
        C('HBsAg', 'IU/mL', '< 0.05 (Non-reactive)', high=0.05),
        S('Interpretation', ['Non-Reactive*', 'Reactive'], ref='Non-Reactive'),
    ], xmlid='hbsag_quantitative'),
    _ab('Anti-HCV', 1200, 'Anti-HCV', xmlid='anti_hcv'),
    _ab('Anti-HBs (Antibody to HBsAg)', 1500, 'Anti-HBs',
        values=None, xmlid='anti_hbs'),
    _ab('Anti-HBc Total', 1200, 'Anti-HBc Total', xmlid='anti_hbc_total'),
    _ab('Anti-HBe Total', 1200, 'Anti-HBe', xmlid='anti_hbe_total'),
    _ab('HBeAg', 1000, 'HBeAg', xmlid='hbeag'),
    _ab('Anti-HAV (Total)', 1200, 'Anti-HAV Total', xmlid='anti_hav'),
    _ab('Anti-HAV IgM', 1200, 'Anti-HAV IgM', xmlid='anti_hav_igm'),
    _ab('Anti-HEV (Total)', 1200, 'Anti-HEV Total', xmlid='anti_hev'),
    _ab('Anti-HEV IgM', 1200, 'Anti-HEV IgM', xmlid='anti_hev_igm'),

    # ------------------------------------------------------- tumour markers
    _marker('AFP (Alpha Feto Protein)', 1200, 'AFP', 'ng/mL', '< 10', high=10,
            xmlid='afp'),
    _marker('CEA (Carcinoembryonic Antigen)', 1200, 'CEA', 'ng/mL',
            'Non-smoker: < 3.0 | Smoker: < 5.0', high=3.0, xmlid='cea'),
    _marker('CA-125', 1200, 'CA-125', 'U/mL', '< 35', high=35, xmlid='ca_125'),
    _marker('CA-15.3', 1200, 'CA-15.3', 'U/mL', '< 25', high=25, xmlid='ca_15_3'),
    _marker('CA-19.9', 1200, 'CA-19.9', 'U/mL', '< 37', high=37, xmlid='ca_19_9'),
    _imm('Beta-hCG (Quantitative)', 1200, [
        C('Beta-hCG', 'mIU/mL',
          'Non-pregnant: < 5 | Pregnancy: rises with gestational age', high=5),
        T('Comment'),
    ], xmlid='beta_hcg'),

    # --------------------------------------------------------- autoimmunity
    _ab('ANA (Anti Nuclear Antibody)', 1200, 'ANA', xmlid='ana'),
    _ab('Anti-dsDNA', 1600, 'Anti-dsDNA', xmlid='anti_ds_dna'),
    _marker('Anti-CCP', 2200, 'Anti-CCP', 'U/mL', '< 17', high=17, xmlid='anti_ccp'),
    _marker('RA Test (Quantitative)', 800, 'Rheumatoid Factor', 'IU/mL', '< 14',
            high=14, xmlid='ra_test_quantitative'),
    _ab('c-ANCA', 1300, 'c-ANCA (PR3)', xmlid='canca'),
    _ab('p-ANCA', 1300, 'p-ANCA (MPO)', xmlid='panca'),
    _ab('Anti SS-A (Ro) Antibody', 4000, 'Anti SS-A (Ro)', xmlid='anti_ss_a'),
    _ab('Anti SS-B (La) Antibody', 4000, 'Anti SS-B (La)', xmlid='anti_ss_b'),
    _imm('Anti-Cardiolipin Antibody', 4000, [
        H('ANTI-CARDIOLIPIN ANTIBODY'),
        C('aCL IgG', 'GPL-U/mL', '< 12', high=12),
        C('aCL IgM', 'MPL-U/mL', '< 12', high=12),
    ], method=M_ELISA, xmlid='anti_cardiolipin'),
    _marker('Anti-Thyroid Antibody (Anti-TPO)', 2500, 'Anti-TPO', 'IU/mL', '< 34',
            high=34, xmlid='anti_tpo'),
    _marker('Anti-Thyroid Antibody Panel', 2600, 'Anti-TPO', 'IU/mL', '< 34',
            high=34, lab_not_required=True, xmlid='anti_thyroid_ab_panel'),
    _marker('TRAB (TSH Receptor Antibody)', 6000, 'TRAB', 'IU/L', '< 1.75',
            high=1.75, xmlid='trab'),
    _marker('ACh Receptor Antibody', 10090, 'ACh Receptor Antibody', 'nmol/L',
            '< 0.4', high=0.4, xmlid='ach_receptor_antibody'),
    _imm('HLA-B27', 4000, [
        H('HLA-B27 TYPING'),
        S('HLA-B27', _POSNEG, ref='Negative'),
        T('Method', default='Flow cytometry / PCR-SSP'),
        T('Comment', default='A positive result supports, but does not by itself '
                             'establish, a diagnosis of ankylosing spondylitis.'),
    ], layout='special', method='method_pcr', xmlid='hla_b27'),

    # ------------------------------------------------- complement & immunoglobulin
    _marker('Serum C3', 1500, 'Complement C3', 'mg/dL', '90 - 180', low=90, high=180,
            xmlid='serum_c3'),
    _marker('Serum C4', 1500, 'Complement C4', 'mg/dL', '10 - 40', low=10, high=40,
            xmlid='serum_c4'),
    _marker('Total IgE', 1200, 'Total IgE', 'IU/mL', '< 100', high=100, xmlid='total_ige'),

    # ---------------------------------------------------- infection markers
    _marker('Procalcitonin', 2000, 'Procalcitonin', 'ng/mL',
            'Normal: < 0.05 | Systemic infection likely: > 0.5', high=0.05,
            xmlid='procalcitonin'),
    _marker('Interleukin-6 (IL-6)', 2540, 'IL-6', 'pg/mL', '< 7', high=7,
            xmlid='interleukin_6'),
    _marker('ADA (Adenosine Deaminase)', 2000, 'ADA', 'U/L', '< 40', high=40,
            xmlid='ada'),
    _marker('NT-proBNP', 3000, 'NT-proBNP', 'pg/mL', '< 125 (age < 75) | < 450 (age >= 75)',
            high=125, xmlid='nt_pro_bnp'),

    # ------------------------------------------------------ vitamins / other
    _marker('Vitamin B12', 2500, 'Vitamin B12', 'pg/mL', '197 - 771', low=197,
            high=771, xmlid='vitamin_b12'),
    _imm('Vitamin D (25-OH)', 3000, [
        C('25-OH Vitamin D', 'ng/mL',
          'Deficient: < 20 | Insufficient: 20 - 29 | Sufficient: 30 - 100',
          low=30, high=100),
        S('Interpretation', ['Sufficient*', 'Insufficient', 'Deficient', 'Toxic'],
          ref='Sufficient'),
    ], xmlid='vitamin_d'),

    # ------------------------------------------------------------- panels
    _imm('Toxoplasma IgG & IgM', 2800, [
        H('TOXOPLASMA ANTIBODY'),
        S('Toxo IgM', _POSNEGEQ, ref='Negative'),
        S('Toxo IgG', _POSNEGEQ, ref='Negative'),
        T('Interpretation'),
    ], method=M_ELISA, xmlid='toxoplasma_igg_igm'),
    _imm('Anti HSV-1 IgG & IgM', 2800, [
        H('HERPES SIMPLEX VIRUS 1 ANTIBODY'),
        S('HSV-1 IgM', _POSNEGEQ, ref='Negative'),
        S('HSV-1 IgG', _POSNEGEQ, ref='Negative'),
    ], method=M_ELISA, xmlid='anti_hsv1_igg_igm'),
    _imm('Herpes Simplex IgM', 1400, [
        S('HSV IgM', _POSNEGEQ, ref='Negative'),
    ], method=M_ELISA, xmlid='herpes_simplex_igm'),
    _imm('Herpes Simplex IgG', 1400, [
        S('HSV IgG', _POSNEGEQ, ref='Negative'),
    ], method=M_ELISA, xmlid='herpes_simplex_igg'),
    _imm('TORCH Antibody Panel', 9680, [
        H('TOXOPLASMA'),
        S('Toxo IgM', _POSNEGEQ, ref='Negative'),
        S('Toxo IgG', _POSNEGEQ, ref='Negative'),
        H('RUBELLA'),
        S('Rubella IgM', _POSNEGEQ, ref='Negative'),
        S('Rubella IgG', _POSNEGEQ, ref='Negative'),
        H('CYTOMEGALOVIRUS'),
        S('CMV IgM', _POSNEGEQ, ref='Negative'),
        S('CMV IgG', _POSNEGEQ, ref='Negative'),
        H('HERPES SIMPLEX VIRUS'),
        S('HSV IgM', _POSNEGEQ, ref='Negative'),
        S('HSV IgG', _POSNEGEQ, ref='Negative'),
        T('Interpretation'),
    ], method=M_ELISA, lab_not_required=True, required_time=3, xmlid='torch_panel'),

    _imm('QuantiFERON-TB Gold (IGRA)', 8000, [
        H('INTERFERON GAMMA RELEASE ASSAY'),
        C('TB1 Antigen - Nil', 'IU/mL'),
        C('TB2 Antigen - Nil', 'IU/mL'),
        C('Mitogen - Nil', 'IU/mL', '> 0.5 (valid control)', low=0.5),
        S('Result', ['Negative*', 'Positive', 'Indeterminate'], ref='Negative'),
        T('Comment', default='A positive IGRA indicates M. tuberculosis infection; '
                             'it does not distinguish latent from active disease.'),
    ], layout='special', method=M_ELISA, required_time=3, xmlid='quantiferon_tb_gold'),
]
