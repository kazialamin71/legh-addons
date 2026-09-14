"""Vocabularies a transfusion slip is allowed to use.

Free text is how a blood bank ends up with "B+", "B +ve", "B Positive" and
"b pos" all meaning the same group and none of them countable. These are the
only values the slip can carry, and they are shared by the donor register and
the crossmatch result so the two can be compared at all.
"""

BLOOD_GROUPS = [
    ('a_pos', 'A Positive'), ('a_neg', 'A Negative'),
    ('b_pos', 'B Positive'), ('b_neg', 'B Negative'),
    ('ab_pos', 'AB Positive'), ('ab_neg', 'AB Negative'),
    ('o_pos', 'O Positive'), ('o_neg', 'O Negative'),
]

DONATION_TYPES = [
    ('voluntary', 'Voluntary'),
    ('replacement', 'Replacement'),
    ('directed', 'Directed'),
    ('autologous', 'Autologous'),
]

# Whole blood plus the components a hospital blood bank actually issues. A
# component the hospital does not prepare is simply never picked; adding one is
# a line here rather than a free-text convention nobody else knows about.
BLOOD_COMPONENTS = [
    ('whole_blood', 'Whole Blood'),
    ('prbc', 'Packed Red Blood Cells'),
    ('platelet', 'Platelet Concentrate (RDP)'),
    ('sdp', 'Single Donor Platelet (SDP)'),
    ('ffp', 'Fresh Frozen Plasma'),
    ('cryo', 'Cryoprecipitate'),
]

CROSS_MATCH_STATUS = [
    ('compatible', 'Compatible'),
    ('incompatible', 'Incompatible'),
]

SEXES = [('male', 'Male'), ('female', 'Female'), ('other', 'Other')]

# What a screening or compatibility value must NOT say for the unit to be
# issued. Matched case-insensitively against the printed value, so it holds for
# a hospital that words its options "Reactive" rather than "Positive".
UNSAFE_TOKENS = ('positive', 'reactive', 'incompatible', 'detected')
