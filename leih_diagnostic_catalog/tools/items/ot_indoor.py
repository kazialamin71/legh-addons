"""Operation theatre, anaesthesia and indoor (bed / cabin) charges.

All ``service_group='procedure'`` except the bed and food charges, which are
``other``. Items whose rate is genuinely variable (surgeon team charge, implant
charge, machine charges) are seeded at 0 and marked ``manual`` - the billing
clerk types the negotiated figure, and a 0 default makes it obvious when that
step was skipped.

``indoor=True`` marks the items that belong on an admitted patient's statement
rather than an OPD bill.
"""

from catalogue_spec import ITEM
from refs import AC_INDOOR, AC_OT, INDOOR, OT


def _ot(name, rate, xmlid, **kw):
    kw.setdefault('group', 'procedure')
    return ITEM(name, OT, AC_OT, rate, xmlid=xmlid, sample_req=False, **kw)


def _bed(name, rate, xmlid, **kw):
    kw.setdefault('group', 'other')
    kw.setdefault('indoor', True)
    return ITEM(name, INDOOR, AC_INDOOR, rate, xmlid=xmlid, sample_req=False, **kw)


ITEMS = [
    # ------------------------------------------------------- theatre charges
    _ot('OT Charge (First Hour)', 3000, 'ot_charge_first_hour', indoor=True),
    _ot('OT Charge (Second Hour)', 1000, 'ot_charge_second_hour', indoor=True),
    _ot('OT Charge with Sedation', 2000, 'ot_charge_with_sedation'),
    _ot('Outdoor Surgeon OT Charge (Package)', 8000, 'ot_outdoor_surgeon_package'),
    _ot('OT Team Charge', 10000, 'ot_team_charge', indoor=True),
    _ot('OT Team Charge - 2', 5000, 'ot_team_charge_2', indoor=True),
    _ot('Surgeon Team Charge', 0, 'ot_surgeon_team_charge', manual=True, indoor=True),
    _ot('OT Assistant Charge', 0, 'ot_assistant_charge', manual=True),
    _ot('Assistant Doctor Fee', 0, 'ot_assistant_doctor_fee', manual=True),
    _ot('Anaesthesiologist Fee', 0, 'ot_anaesthesiologist_fee', manual=True),
    _ot('Anaesthesia Doctor Fee', 0, 'ot_anaesthesia_doctor_fee', manual=True),
    _ot('Isoflurane Charge', 1000, 'ot_isoflurane_charge'),
    _ot('Labour Room Charge', 2000, 'ot_labour_room_charge',
        lab_not_required=True, indoor=True),

    # ------------------------------------------------------ equipment charges
    _ot('Ligasure Machine Charge', 0, 'ot_ligasure_machine', manual=True),
    _ot('Laparoscopy Machine Charge', 0, 'ot_laparoscopy_machine', manual=True),
    _ot('Circular Stapler', 0, 'ot_circular_stapler', manual=True, group='consumable'),
    _ot('Cutting Stapler', 0, 'ot_cutting_stapler', manual=True, group='consumable'),
    _ot('Implant Charge', 0, 'ot_implant_charge', manual=True,
        lab_not_required=True, group='consumable'),

    # -------------------------------------------------------- post-operative
    _ot('Post Operative Charge (First Four Hours)', 1000, 'ot_post_op_first_4h',
        indoor=True),
    _ot('Post Operative Charge (More Than Four Hours)', 1500, 'ot_post_op_over_4h',
        indoor=True),
    _ot('Monitor Charge for Post Operative (Per Day)', 500, 'ot_post_op_monitor',
        indoor=True),
    _ot('Oxygen Charge for Post Operative', 500, 'ot_post_op_oxygen',
        group='oxygen', indoor=True),

    # -------------------------------------------------- ophthalmic procedures
    _ot('Socket Reconstruction - A', 16000, 'ot_socket_reconstruction_a'),
    _ot('Socket Reconstruction - B', 20000, 'ot_socket_reconstruction_b'),
    _ot('Socket Reconstruction - C', 25000, 'ot_socket_reconstruction_c'),
    _ot('Canalicular Reconstruction - A', 8000, 'ot_canalicular_reconstruction_a'),
    _ot('Canalicular Reconstruction - B', 12000, 'ot_canalicular_reconstruction_b'),
    _ot('Punctoplasty - A', 4000, 'ot_punctoplasty_a'),
    _ot('Punctoplasty - B', 6000, 'ot_punctoplasty_b'),
    _ot('Bandage Contact Lens (BCL)', 1000, 'ot_bandage_contact_lens'),
    _ot('Reposition of IOL (OPD Patient)', 5000, 'ot_reposition_iol'),
    _ot('Reposition of IOL (OPD Patient - Lions Case)', 1000, 'ot_reposition_iol_lions'),

    # ----------------------------------------------------- general procedures
    _ot('Procedure Charge - Local Anaesthesia Only', 1500, 'ot_procedure_local_anaesthesia'),
    _ot('Lumbar Puncture', 4000, 'ot_lumbar_puncture'),
    _ot('Copper-T Insertion', 4000, 'ot_copper_t', lab_not_required=True),

    # ------------------------------------------------- admission & bed charges
    _bed('Admission Charge', 1000, 'indoor_admission_charge'),
    _bed('Admission Fee (Outside Referral)', 1500, 'indoor_admission_fee_outside'),
    _bed('Ward Bed Charge', 2000, 'indoor_ward_bed_charge'),
    _bed('Cabin Charge', 5000, 'indoor_cabin_charge'),
    _bed('Share Cabin Charge', 3500, 'indoor_share_cabin_charge'),
    _bed('HDU Bed Charge', 7000, 'indoor_hdu_bed_charge'),
    _bed('Baby Cot Bed', 1000, 'indoor_baby_cot_bed'),
    _bed('Food Cost', 800, 'indoor_food_cost'),
    _bed("Consultant's Fee (Indoor Round)", 1000, 'indoor_consultant_fee',
         group='consultation'),
    _bed('Service Charge', 0, 'indoor_service_charge', manual=True),
    _bed('Medicine Charge', 0, 'indoor_medicine_charge', manual=True),
    _bed('Medicine Total', 0, 'indoor_medicine_total', manual=True),
    _bed('Out Medicine Fee', 0, 'indoor_out_medicine_fee', manual=True),
    _bed('Ambulance Service Fee', 0, 'indoor_ambulance_service_fee', manual=True),
    _bed('Infusion Pump Charge (Per Day)', 0, 'indoor_infusion_pump_charge', manual=True),
    _bed('Other Charges', 0, 'indoor_other_charges', manual=True),
]
