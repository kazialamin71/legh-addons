"""Declarative catalogue spec + XML emitter.

The catalogue is authored here as Python literals and *generated* into
``data/1x_*.xml`` .. ``data/3x_*.xml`` by ``build_catalogue.py``. Hand-editing
the generated XML is a dead end - edit this file and re-run the builder:

    python3 tools/build_catalogue.py

Why a generator at all: the catalogue is ~400 items and ~900 components. Written
straight into XML that is 6000+ lines in which a wrong reference range is
invisible. Here a test is one readable line and the reference ranges line up in
columns, so they can actually be reviewed against a lab manual.
"""

import re
import unicodedata

# --------------------------------------------------------------------------
# Component helpers
# --------------------------------------------------------------------------


def H(name):
    """A bold section header inside a report (not an editable component)."""
    return {'kind': 'header', 'name': name}


def C(name, uom='', ref='', low=None, high=None, crit_low=None, crit_high=None,
      male='', female='', child=''):
    """A numeric component.

    ``low``/``high`` drive the automatic H/L flag on the result; ``crit_*``
    drive the critical HH/LL flag. ``ref`` is what actually prints - keep it in
    the lab's own wording, including qualifiers like "< 200" that no numeric
    pair can express.
    """
    return {'kind': 'numeric', 'name': name, 'uom': uom, 'ref': ref,
            'low': low, 'high': high, 'crit_low': crit_low, 'crit_high': crit_high,
            'male': male, 'female': female, 'child': child}


def S(name, values, ref='', uom=''):
    """A selection component. Mark the default value with a trailing '*'."""
    return {'kind': 'selection', 'name': name, 'uom': uom, 'ref': ref, 'values': values}


def T(name, default='', uom='', ref=''):
    """A free-text component."""
    return {'kind': 'text', 'name': name, 'uom': uom, 'ref': ref, 'default': default}


def COND(component, on, when):
    """Show ``component`` only when the component named ``on`` equals ``when``."""
    component = dict(component)
    component['parent'] = on
    component['parent_value'] = when
    return component


# --------------------------------------------------------------------------
# Item helper
# --------------------------------------------------------------------------


def ITEM(name, dept, account, rate, xmlid=None, group='diagnostic',
         category='pathology', layout='tabular', tube=None, sample=None,
         method=None, instrument=None, sample_req=None, lab_not_required=False,
         manual=False, indoor=False, individual=False, merge=False,
         required_time=0, own_tube=False, antibiotics=None, templates=None,
         incubation=None, medium=None, components=()):
    """One catalogue item.

    ``sample_req`` defaults to True for lab work that has a tube and False for
    everything else, which is the distinction leih19 uses to decide whether a
    lab.specimen is created at billing time.
    """
    if sample_req is None:
        sample_req = bool(tube)
    return {
        'name': name, 'dept': dept, 'account': account, 'rate': rate,
        'xmlid': xmlid or slug(name), 'group': group, 'category': category,
        'layout': layout, 'tube': tube, 'sample': sample, 'method': method,
        'instrument': instrument, 'sample_req': sample_req,
        'lab_not_required': lab_not_required, 'manual': manual, 'indoor': indoor,
        'individual': individual, 'merge': merge, 'required_time': required_time,
        'own_tube': own_tube, 'antibiotics': antibiotics, 'templates': templates,
        'incubation': incubation, 'medium': medium,
        'components': list(components),
    }


_SLUG_RE = re.compile(r'[^a-z0-9]+')


def slug(name):
    """Stable xmlid fragment from an item name."""
    text = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    text = _SLUG_RE.sub('_', text.lower()).strip('_')
    return text[:60].rstrip('_')
