#!/usr/bin/env python3
"""Generate the catalogue data XML from the specs in ``tools/items/``.

Run from the module root:

    python3 tools/build_catalogue.py

Every file it writes carries a "generated" banner. Edit the spec, not the XML.
"""

import importlib
import os
import sys
from xml.sax.saxutils import escape, quoteattr

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from panels import PANELS  # noqa: E402

# spec module -> (output file, section heading)
SECTIONS = [
    ('biochemistry',        '10_biochemistry.xml',        'Biochemistry'),
    ('haematology',         '11_haematology.xml',         'Haematology'),
    ('clinical_pathology',  '12_clinical_pathology.xml',  'Clinical Pathology'),
    ('serology',            '13_serology.xml',            'Serology'),
    ('immunology',          '14_immunology.xml',          'Immunology'),
    ('hormone',             '15_hormone.xml',             'Hormone & Endocrinology'),
    ('microbiology',        '16_microbiology.xml',        'Microbiology'),
    ('histocytopathology',  '17_histocytopathology.xml',  'Histopathology & Cytopathology'),
    ('transfusion',         '18_transfusion.xml',         'Transfusion Medicine'),
    ('radiology',           '20_radiology.xml',           'Radiology (X-Ray / CT / MRI)'),
    ('usg',                 '21_usg.xml',                 'Ultrasonography'),
    ('cardiology',          '22_cardiology.xml',          'Cardiac Investigations'),
    ('dental',              '30_dental.xml',              'Dental'),
    ('ot_indoor',           '31_ot_indoor.xml',           'Operation Theatre & Indoor'),
    ('general_services',    '32_general_services.xml',    'Nursing & General Services'),
    ('packages',            '33_packages.xml',            'Health Checkup Packages'),
    ('consumables',         '34_consumables.xml',         'Consumables & Disposables'),
]

BANNER = """<?xml version="1.0" encoding="UTF-8"?>
<!--
    {title} - {count} catalogue items.

    GENERATED FILE - do not edit by hand.
    Source: tools/items/{spec}.py    Rebuild: python3 tools/build_catalogue.py

    Rates carried over from the legacy export are PROVISIONAL and are expected
    to be revised before go-live.
-->
<odoo noupdate="1">
"""


def _f(name, value):
    return '        <field name=%s>%s</field>\n' % (quoteattr(name), escape(str(value)))


def _ref(name, value):
    return '        <field name=%s ref=%s/>\n' % (quoteattr(name), quoteattr(value))


def _bool(name, value):
    return '        <field name=%s eval="%s"/>\n' % (quoteattr(name), 'True' if value else 'False')


def emit_item(out, item):
    xid = item['xmlid']
    out.append('    <!-- %s -->\n' % item['name'])
    out.append('    <record id=%s model="examination.entry">\n' % quoteattr(xid))
    out.append(_f('name', item['name']))
    out.append(_ref('department', item['dept']))
    out.append(_ref('accounts_id', item['account']))
    out.append(_f('rate', item['rate']))
    out.append(_f('base_rate', item['rate']))
    out.append(_f('service_group', item['group']))
    if item['group'] == 'diagnostic':
        out.append(_f('category', item['category']))
        out.append(_f('report_layout', item['layout']))
    out.append(_f('report_type', _report_type(item)))
    if item['tube']:
        out.append(_ref('tube_color_id', item['tube']))
    if item['sample']:
        out.append(_ref('sample_type', item['sample']))
    if item['method']:
        out.append(_ref('default_method_id', item['method']))
    if item['instrument']:
        out.append(_ref('default_instrument_id', item['instrument']))
    out.append(_bool('sample_req', item['sample_req']))
    if item['lab_not_required']:
        out.append(_bool('lab_not_required', True))
    if item['manual']:
        out.append(_bool('manual', True))
    if item['indoor']:
        out.append(_bool('indoor', True))
    if item['individual']:
        out.append(_bool('individual', True))
    if item['merge']:
        out.append(_bool('merge', True))
    if item['own_tube']:
        out.append(_bool('needs_separate_tube', True))
    if item['required_time']:
        out.append(_f('required_time', item['required_time']))
    if item['incubation']:
        hours, temp = item['incubation']
        out.append(_f('default_incubation_hours', hours))
        out.append(_f('default_incubation_temp_c', temp))
    if item['medium']:
        out.append(_f('default_culture_medium', item['medium']))
    if item['antibiotics']:
        refs = PANELS[item['antibiotics']]
        joined = ',\n            '.join("ref('%s')" % r for r in refs)
        out.append('        <field name="antibiotic_ids" eval="[(6, 0, [\n            %s,\n        ])]"/>\n' % joined)
    if item['templates']:
        joined = ',\n            '.join("ref('%s')" % r for r in item['templates'])
        out.append('        <field name="report_template_ids" eval="[(6, 0, [\n            %s,\n        ])]"/>\n' % joined)
    out.append('    </record>\n\n')

    emit_components(out, item)


def _report_type(item):
    """`report_type` is the coarse print family; `report_layout` is the detail."""
    if item['group'] != 'diagnostic':
        return 'other'
    if item['category'] == 'radiology':
        return 'radiology'
    if item['category'] == 'descriptive':
        return 'descriptive'
    return 'pathology'


def emit_components(out, item):
    xid = item['xmlid']
    line_xid = {}
    value_xid = {}

    for index, comp in enumerate(item['components'], start=1):
        cid = '%s_c%02d' % (xid, index)
        line_xid[comp['name']] = cid
        out.append('    <record id=%s model="examination.entry.line">\n' % quoteattr(cid))
        out.append(_f('name', comp['name']))
        out.append(_ref('examinationentry_id', xid))
        out.append(_f('sequence', index * 10))
        if comp['kind'] == 'header':
            out.append(_bool('is_group_header', True))
            out.append(_bool('bold', True))
            out.append(_f('result_type', 'text'))
            out.append('    </record>\n\n')
            continue
        out.append(_f('result_type', 'numeric' if comp['kind'] == 'numeric' else
                                    ('selection' if comp['kind'] == 'selection' else 'text')))
        if comp.get('uom'):
            out.append(_f('uom', comp['uom']))
        if comp.get('ref'):
            out.append(_f('reference_value', comp['ref']))
        if comp.get('male'):
            out.append(_f('reference_value_male', comp['male']))
        if comp.get('female'):
            out.append(_f('reference_value_female', comp['female']))
        if comp.get('child'):
            out.append(_f('reference_value_child', comp['child']))
        for key, field in (('low', 'ref_low'), ('high', 'ref_high'),
                           ('crit_low', 'critical_low'), ('crit_high', 'critical_high')):
            if comp.get(key) is not None:
                out.append(_f(field, comp[key]))
        if comp.get('default'):
            out.append(_f('default_value', comp['default']))
        out.append('    </record>\n\n')

        for vindex, raw in enumerate(comp.get('values', ()), start=1):
            is_default = raw.endswith('*')
            label = raw[:-1] if is_default else raw
            vid = '%s_v%02d' % (cid, vindex)
            value_xid[(comp['name'], label)] = vid
            out.append('    <record id=%s model="examination.possible.value">\n' % quoteattr(vid))
            out.append(_f('name', label))
            out.append(_ref('examination_line_id', cid))
            out.append(_f('sequence', vindex * 10))
            if is_default:
                out.append(_bool('is_default', True))
            out.append('    </record>\n\n')

    # Conditional visibility is wired in a second pass: a line can only point at
    # a possible value that has already been created.
    conditionals = [c for c in item['components'] if c.get('parent')]
    if conditionals:
        out.append('    <!-- conditional display -->\n')
    for comp in conditionals:
        key = (comp['parent'], comp['parent_value'])
        if key not in value_xid:
            raise SystemExit(
                'ERROR in %r: component %r depends on %r == %r, but that value '
                'is not defined on the parent component.'
                % (item['name'], comp['name'], comp['parent'], comp['parent_value']))
        out.append('    <record id=%s model="examination.entry.line">\n'
                   % quoteattr(line_xid[comp['name']]))
        out.append(_ref('parent_line_id', line_xid[comp['parent']]))
        out.append(_ref('show_when_value_id', value_xid[key]))
        out.append('    </record>\n\n')


def main():
    total = 0
    seen = {}
    for spec, filename, title in SECTIONS:
        module = importlib.import_module('items.%s' % spec)
        items = module.ITEMS
        out = [BANNER.format(title=title, count=len(items), spec=spec)]
        for item in items:
            if item['xmlid'] in seen:
                raise SystemExit('ERROR: duplicate xmlid %r (%r and %r)'
                                 % (item['xmlid'], seen[item['xmlid']], item['name']))
            seen[item['xmlid']] = item['name']
            emit_item(out, item)
        out.append('</odoo>\n')
        path = os.path.join(MODULE_ROOT, 'data', filename)
        with open(path, 'w') as handle:
            handle.write(''.join(out))
        comps = sum(len(i['components']) for i in items)
        print('%-32s %3d items %4d components' % (filename, len(items), comps))
        total += len(items)
    print('%-32s %3d items total' % ('TOTAL', total))


if __name__ == '__main__':
    main()
