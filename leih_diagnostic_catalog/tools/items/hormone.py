"""Hormone & Endocrinology.

Reproductive hormones vary by menstrual phase far more than by any single
"normal range", so those print the phase bands in ``ref`` and leave the numeric
flag thresholds unset - an auto-flag against a follicular range would mark every
normal mid-cycle LH as high.
"""

from catalogue_spec import C, H, ITEM, S, T
from refs import AC_HORMONE, HORMONE, I_IMM, M_CLIA, SP_SERUM, T_GOLD


def _horm(name, rate, components, **kw):
    kw.setdefault('tube', T_GOLD)
    kw.setdefault('sample', SP_SERUM)
    kw.setdefault('method', M_CLIA)
    kw.setdefault('instrument', I_IMM)
    return ITEM(name, HORMONE, AC_HORMONE, rate, components=components, **kw)


def _one(name, rate, analyte, uom, ref, low=None, high=None, **kw):
    return _horm(name, rate, [C(analyte, uom, ref, low=low, high=high, **kw.pop('ranges', {}))], **kw)


ITEMS = [
    # ---------------------------------------------------------- thyroid axis
    _one('TSH', 800, 'TSH', 'uIU/mL', '0.35 - 4.94', low=0.35, high=4.94,
         xmlid='tsh'),
    _one('T3 (Total Triiodothyronine)', 800, 'T3', 'ng/mL', '0.58 - 1.59',
         low=0.58, high=1.59, xmlid='t3'),
    _one('T4 (Total Thyroxine)', 800, 'T4', 'ug/dL', '4.87 - 11.72',
         low=4.87, high=11.72, xmlid='t4'),
    _one('FT3 (Free T3)', 1000, 'FT3', 'pg/mL', '1.71 - 3.71', low=1.71, high=3.71,
         xmlid='ft3'),
    _one('FT4 (Free T4)', 1000, 'FT4', 'ng/dL', '0.70 - 1.48', low=0.70, high=1.48,
         xmlid='ft4'),

    # ------------------------------------------------------- pituitary axis
    _horm('LH (Luteinizing Hormone)', 1200, [
        C('LH', 'mIU/mL',
          'Follicular: 2.4 - 12.6 | Mid-cycle: 14.0 - 95.6 | Luteal: 1.0 - 11.4 | '
          'Post-menopausal: 7.7 - 58.5 | Male: 1.7 - 8.6',
          male='1.7 - 8.6'),
        S('Menstrual Phase',
          ['Not Applicable*', 'Follicular', 'Mid-cycle (Ovulatory)', 'Luteal',
           'Post-menopausal'], ref='Not Applicable'),
    ], xmlid='lh'),
    _horm('FSH (Follicle Stimulating Hormone)', 1200, [
        C('FSH', 'mIU/mL',
          'Follicular: 3.5 - 12.5 | Mid-cycle: 4.7 - 21.5 | Luteal: 1.7 - 7.7 | '
          'Post-menopausal: 25.8 - 134.8 | Male: 1.5 - 12.4',
          male='1.5 - 12.4'),
        S('Menstrual Phase',
          ['Not Applicable*', 'Follicular', 'Mid-cycle (Ovulatory)', 'Luteal',
           'Post-menopausal'], ref='Not Applicable'),
    ], xmlid='fsh'),
    _one('Prolactin', 1200, 'Prolactin', 'ng/mL', 'M: 4.0 - 15.2  F: 4.8 - 23.3',
         low=4.0, high=23.3, xmlid='prolactin'),
    _horm('Growth Hormone (GH)', 1500, [
        C('Growth Hormone', 'ng/mL', 'M: < 3.0  F: < 8.0', high=8.0,
          male='< 3.0', female='< 8.0'),
        T('Comment', default='Random GH has limited diagnostic value; interpret with '
                             'a suppression or stimulation test.'),
    ], xmlid='growth_hormone'),
    _one('ACTH', 2200, 'ACTH', 'pg/mL', '7.2 - 63.3 (morning sample)',
         low=7.2, high=63.3, xmlid='acth'),
    _one('PTH (Parathyroid Hormone)', 1200, 'Intact PTH', 'pg/mL', '15 - 65',
         low=15, high=65, xmlid='pth'),

    # ----------------------------------------------------------- adrenal
    _one('Cortisol (Basal - 9:00 AM)', 1200, 'Cortisol (AM)', 'ug/dL',
         '6.2 - 19.4', low=6.2, high=19.4, xmlid='cortisol_am'),
    _one('Cortisol (Evening - 5:00 PM)', 1200, 'Cortisol (PM)', 'ug/dL',
         '2.3 - 11.9', low=2.3, high=11.9, xmlid='cortisol_pm'),

    # ------------------------------------------------------- reproductive
    _horm('Testosterone (Total)', 1500, [
        C('Total Testosterone', 'ng/mL', 'M: 2.49 - 8.36  F: 0.084 - 0.481',
          male='2.49 - 8.36', female='0.084 - 0.481'),
    ], xmlid='testosterone_total'),
    _horm('Free Testosterone', 2800, [
        C('Free Testosterone', 'pg/mL', 'M: 8.7 - 54.7  F: 0.3 - 3.2',
          male='8.7 - 54.7', female='0.3 - 3.2'),
    ], xmlid='free_testosterone'),
    _one('DHT (Dihydrotestosterone)', 3500, 'DHT', 'ng/dL',
         'M: 30 - 85  F: 4 - 22', xmlid='dht'),
    _horm('Oestrogen (Estradiol / E2)', 1000, [
        C('Estradiol (E2)', 'pg/mL',
          'Follicular: 12.5 - 166 | Mid-cycle: 85.8 - 498 | Luteal: 43.8 - 211 | '
          'Post-menopausal: < 54.7 | Male: 7.6 - 42.6',
          male='7.6 - 42.6'),
        S('Menstrual Phase',
          ['Not Applicable*', 'Follicular', 'Mid-cycle (Ovulatory)', 'Luteal',
           'Post-menopausal'], ref='Not Applicable'),
    ], xmlid='oestrogen_estradiol'),
    _horm('Progesterone', 1000, [
        C('Progesterone', 'ng/mL',
          'Follicular: 0.181 - 2.84 | Luteal: 5.82 - 75.9 | '
          'Post-menopausal: < 0.401 | Male: < 0.149'),
        S('Menstrual Phase',
          ['Not Applicable*', 'Follicular', 'Luteal', 'Post-menopausal'],
          ref='Not Applicable'),
    ], xmlid='progesterone'),
    _horm('AMH (Anti-Mullerian Hormone)', 3000, [
        C('AMH', 'ng/mL',
          'Adequate ovarian reserve: 1.0 - 4.0 | Low: < 1.0 | PCOS pattern: > 4.0',
          low=1.0, high=4.0),
        T('Comment'),
    ], xmlid='amh'),

    # ------------------------------------------------------------- prostate
    _one('PSA (Total)', 1200, 'Total PSA', 'ng/mL', '< 4.0', high=4.0, xmlid='psa_total'),
    _horm('tPSA & fPSA (with Ratio)', 800, [
        H('PROSTATE SPECIFIC ANTIGEN'),
        C('Total PSA (tPSA)', 'ng/mL', '< 4.0', high=4.0),
        C('Free PSA (fPSA)', 'ng/mL'),
        C('Free / Total PSA Ratio', '%', '> 25 (favours benign disease)', low=25),
    ], xmlid='tpsa_fpsa'),
]
