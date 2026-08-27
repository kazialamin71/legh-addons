"""Histopathology & Cytopathology.

Narrative layout throughout: these reports are prose written by the
pathologist against a structured skeleton, not a grid of numbers. The
components capture the parts that must never be left to free text (specimen
identity, adequacy, the Bethesda category), and the narrative body carries the
description and diagnosis.
"""

from catalogue_spec import C, H, ITEM, S, T
from refs import (AC_HISTOCYTO, HISTOCYTO, I_MICRO, M_MICRO, M_PAP, SP_SMEAR,
                  SP_TISSUE, T_FORMALIN)

ITEMS = [
    ITEM("Pap's Smear for Cytology", HISTOCYTO, AC_HISTOCYTO, 800,
         xmlid='paps_smear_cytology', category='descriptive', layout='narrative',
         tube=T_FORMALIN, sample=SP_SMEAR, method=M_PAP, instrument=I_MICRO,
         required_time=5, components=[
             H('SPECIMEN'),
             T('Specimen Type', default='Cervical smear (conventional)'),
             T('Clinical History / LMP'),
             H('ADEQUACY'),
             S('Specimen Adequacy',
               ['Satisfactory for Evaluation*',
                'Satisfactory - obscured by blood / inflammation',
                'Unsatisfactory - repeat advised'],
               ref='Satisfactory for Evaluation'),
             S('Endocervical / Transformation Zone Component',
               ['Present*', 'Absent'], ref='Present'),
             H('INTERPRETATION (BETHESDA 2014)'),
             S('Category',
               ['Negative for Intraepithelial Lesion or Malignancy (NILM)*',
                'ASC-US', 'ASC-H', 'LSIL', 'HSIL',
                'Atypical Glandular Cells (AGC)',
                'Squamous Cell Carcinoma', 'Adenocarcinoma',
                'Other - see comment'],
               ref='Negative for Intraepithelial Lesion or Malignancy (NILM)'),
             S('Organisms',
               ['None Identified*', 'Bacterial Vaginosis', 'Candida species',
                'Trichomonas vaginalis', 'Actinomyces', 'Herpes Simplex Virus'],
               ref='None Identified'),
             T('Recommendation',
               default='Routine screening at the interval appropriate for the '
                       'patient age and history.'),
         ]),

    ITEM('Histopathology (Tissue Biopsy)', HISTOCYTO, AC_HISTOCYTO, 2500,
         xmlid='histopathology_biopsy', category='descriptive', layout='narrative',
         tube=T_FORMALIN, sample=SP_TISSUE, method=M_MICRO, instrument=I_MICRO,
         required_time=7, own_tube=True, components=[
             H('SPECIMEN'),
             T('Specimen / Site'),
             T('Clinical History'),
             C('Number of Blocks', ''),
             H('MACROSCOPIC EXAMINATION'),
             T('Gross Description'),
         ]),

    ITEM('FNAC (Fine Needle Aspiration Cytology)', HISTOCYTO, AC_HISTOCYTO, 1500,
         xmlid='fnac', category='descriptive', layout='narrative',
         tube=T_FORMALIN, sample=SP_SMEAR, method=M_MICRO, instrument=I_MICRO,
         required_time=3, components=[
             H('SPECIMEN'),
             T('Site Aspirated'),
             S('Aspirate Adequacy', ['Adequate*', 'Inadequate - repeat advised'],
               ref='Adequate'),
             T('Clinical History'),
         ]),
]
