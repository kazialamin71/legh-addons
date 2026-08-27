"""Cardiac investigations - ECG and echocardiography.

Echo studies carry the measurement components as well as the narrative
template: EF and chamber dimensions are the numbers a cardiologist trends
across visits, and burying them in prose makes that impossible.
"""

from catalogue_spec import C, H, ITEM, S, T
from refs import AC_ECG, AC_ECHO, ECG, ECHO

_ECHO_COMPONENTS = [
    H('MEASUREMENTS'),
    C('LVIDd', 'mm', '37 - 56', low=37, high=56),
    C('LVIDs', 'mm', '20 - 40', low=20, high=40),
    C('IVSd', 'mm', '6 - 11', low=6, high=11),
    C('LVPWd', 'mm', '6 - 11', low=6, high=11),
    C('Left Atrium', 'mm', '19 - 40', low=19, high=40),
    C('Aortic Root', 'mm', '20 - 37', low=20, high=37),
    H('FUNCTION'),
    C('Ejection Fraction (EF)', '%', '> 55', low=55, crit_low=30),
    C('Fractional Shortening (FS)', '%', '25 - 45', low=25, high=45),
    S('Diastolic Function',
      ['Normal*', 'Grade I (Impaired Relaxation)', 'Grade II (Pseudonormal)',
       'Grade III (Restrictive)'], ref='Normal'),
    C('RVSP (estimated)', 'mmHg', '< 35', high=35),
    S('Pericardial Effusion', ['Absent*', 'Trivial', 'Mild', 'Moderate', 'Large'],
      ref='Absent'),
    T('Impression'),
]

ITEMS = [
    ITEM('ECG (12 Lead)', ECG, AC_ECG, 400, xmlid='ecg', category='descriptive',
         layout='narrative', sample_req=False, templates=['tpl_ecg'], components=[
             H('ECG MEASUREMENTS'),
             C('Heart Rate', 'bpm', '60 - 100', low=60, high=100,
               crit_low=40, crit_high=150),
             C('PR Interval', 'ms', '120 - 200', low=120, high=200),
             C('QRS Duration', 'ms', '< 120', high=120),
             C('QTc Interval', 'ms', 'M: < 450  F: < 460', high=460, crit_high=500),
             S('Rhythm', ['Sinus Rhythm*', 'Sinus Bradycardia', 'Sinus Tachycardia',
                          'Atrial Fibrillation', 'Atrial Flutter', 'Paced',
                          'Other - see impression'], ref='Sinus Rhythm'),
             T('Impression'),
         ]),

    ITEM('Echocardiogram (2D)', ECHO, AC_ECHO, 1500, xmlid='echo_2d',
         category='descriptive', layout='narrative', sample_req=False,
         templates=['tpl_echo_2d'], components=_ECHO_COMPONENTS),

    ITEM('Echocardiogram with Colour Doppler', ECHO, AC_ECHO, 2600,
         xmlid='echo_colour_doppler', category='descriptive', layout='narrative',
         sample_req=False, lab_not_required=True, templates=['tpl_echo_2d'],
         components=_ECHO_COMPONENTS + [
             H('COLOUR DOPPLER'),
             S('Mitral Regurgitation', ['None*', 'Trivial', 'Mild', 'Moderate', 'Severe'],
               ref='None'),
             S('Aortic Regurgitation', ['None*', 'Trivial', 'Mild', 'Moderate', 'Severe'],
               ref='None'),
             S('Tricuspid Regurgitation', ['None*', 'Trivial', 'Mild', 'Moderate', 'Severe'],
               ref='None'),
             S('Intracardiac Shunt', ['Not Detected*', 'ASD', 'VSD', 'PDA'],
               ref='Not Detected'),
         ]),

    ITEM('Portable Echocardiography (Bedside)', ECHO, AC_ECHO, 4000,
         xmlid='echo_portable', category='descriptive', layout='narrative',
         sample_req=False, indoor=True, templates=['tpl_echo_2d'],
         components=_ECHO_COMPONENTS),
]
