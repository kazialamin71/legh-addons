"""The default hospital income chart.

Used by the *Set Up Income Heads* button on the hospital accounting settings.
It is a plain list rather than an XML data file because it has to be applied to
a chart that already exists: the button matches every row **by code**, creates
only what is missing, never renames an account somebody already uses, and sets
``parent_id`` only where none has been chosen by hand. Running it twice changes
nothing.

Structure, three levels at most::

    401100 Diagnostic & Imaging Income
        401101..401109  laboratory        (existing)
        401110          lab, unclassified  -> service type 'diagnostic'
        401200 Imaging Income
            401201..401204                (existing)
        401300 Cardiac Investigation Income
            401301..401302                (existing)
    401400 Therapy & Dental Income
        401401 Dental                     (existing)  -> 'dental'
        401402 Physiotherapy                          -> 'physiotherapy'
    402000 Indoor (IPD) Income
        402100 Admission & Registration               -> 'admission'
        402200 Bed & Cabin Income
            402201 General Bed Charge                 -> 'bed'
            402202 Cabin Charge                       -> 'cabin'
        402300 ICU Income
            402301 ICU Bed Charge                     -> 'icu'
        402400 NICU Income
            402401 NICU Bed Charge                    -> 'nicu'
        402500 HDU Income
            402501 HDU Bed Charge                     -> 'hdu'
        402600 Oxygen & Life Support                  -> 'oxygen'
        402900 Other Indoor Charges                   -> 'other'
    403000 Professional Fee Income
        403100 Doctor Visit Fee (Indoor)              -> 'doctor'
        403200 Consultation Fee Income                -> 'consultation'
    401501 Operation Theatre & Procedures (existing)  -> 'procedure'
    404000 Pharmacy Income
        404100 Pharmacy Sales - Indoor                -> 'medicine'

A row carrying ``service_type`` is a *posting* head: it is what the service-type
map points at. A row without one is either a roll-up parent -- never posted to,
and the map refuses to point at it -- or an existing leaf that is only being
given a parent so the hierarchy report adds it up.
"""

# (code, name, parent code or None, service type or None)
HOSPITAL_INCOME_HEADS = [
    # -------------------------------------------------- diagnostics & imaging
    ('401100', 'Diagnostic & Imaging Income', None, None),
    ('401101', 'Diagnostic Income - Biochemistry', '401100', None),
    ('401102', 'Diagnostic Income - Haematology', '401100', None),
    ('401103', 'Diagnostic Income - Clinical Pathology', '401100', None),
    ('401104', 'Diagnostic Income - Serology', '401100', None),
    ('401105', 'Diagnostic Income - Immunology', '401100', None),
    ('401106', 'Diagnostic Income - Hormone & Endocrinology', '401100', None),
    ('401107', 'Diagnostic Income - Microbiology', '401100', None),
    ('401108', 'Diagnostic Income - Histopathology & Cytopathology', '401100', None),
    ('401109', 'Diagnostic Income - Transfusion Medicine', '401100', None),
    ('401110', 'Diagnostic Income - Unclassified', '401100', 'diagnostic'),
    ('401200', 'Imaging Income', '401100', None),
    ('401201', 'Imaging Income - X-Ray', '401200', None),
    ('401202', 'Imaging Income - Ultrasonography', '401200', None),
    ('401203', 'Imaging Income - CT Scan', '401200', None),
    ('401204', 'Imaging Income - MRI', '401200', None),
    ('401300', 'Cardiac Investigation Income', '401100', None),
    ('401301', 'Cardiac Investigation Income - ECG', '401300', None),
    ('401302', 'Cardiac Investigation Income - Echocardiography', '401300', None),

    # ------------------------------------------------------ therapy & dental
    ('401400', 'Therapy & Dental Income', None, None),
    ('401401', 'Service Income - Dental', '401400', 'dental'),
    ('401402', 'Service Income - Physiotherapy', '401400', 'physiotherapy'),

    # ------------------------------------------------------- indoor / ward
    ('402000', 'Indoor (IPD) Income', None, None),
    ('402100', 'Admission & Registration Income', '402000', 'admission'),
    ('402200', 'Bed & Cabin Income', '402000', None),
    ('402201', 'General Bed Charge', '402200', 'bed'),
    ('402202', 'Cabin Charge', '402200', 'cabin'),
    ('402300', 'ICU Income', '402000', None),
    ('402301', 'ICU Bed Charge', '402300', 'icu'),
    ('402400', 'NICU Income', '402000', None),
    ('402401', 'NICU Bed Charge', '402400', 'nicu'),
    ('402500', 'HDU Income', '402000', None),
    ('402501', 'HDU Bed Charge', '402500', 'hdu'),
    ('402600', 'Oxygen & Life Support Income', '402000', 'oxygen'),
    ('402900', 'Other Indoor Charges', '402000', 'other'),

    # --------------------------------------------------------- professional
    ('403000', 'Professional Fee Income', None, None),
    ('403100', 'Doctor Visit Fee (Indoor)', '403000', 'doctor'),
    ('403200', 'Consultation Fee Income', '403000', 'consultation'),
    ('401501', 'Service Income - Operation Theatre & Procedures', '403000', 'procedure'),

    # ------------------------------------------------------------- pharmacy
    ('404000', 'Pharmacy Income', None, None),
    ('404100', 'Pharmacy Sales - Indoor', '404000', 'medicine'),
]
