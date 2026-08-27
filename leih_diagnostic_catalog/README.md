# LEIS Diagnostic Catalogue

Rebuilds the diagnostic and service catalogue from the legacy `examination.entry`
export into properly structured master data.

## What was wrong with the export

The source file (`examination.entry(1).csv`, 396 unique items) had:

| Problem | Scale |
|---|---|
| Items with **no department at all** | 47 |
| Misspelt / inconsistent departments | `Diagonistic`, `Radiolgy & Imaging`, `Micro-biology`, `Hospital > Diagnostic` |
| Items with **no components** | 285 of 396 |
| **Antibiotics stored as result components** | 11 culture tests, up to 36 fake components each |
| Reference ranges | essentially none |
| Units | on a handful of components only |
| Duplicate / misspelt twins | `Hb%` / `Haemoglobin` / `Hemoglobin`, `S.FREEITIN LEVEL` / `S. Feritin` / `Ferritin`, `Raticulocyte` / `Reticulocyte`, ... |

The antibiotic problem is the substantive one. Storing `Ciprofloxacin` as an
`examination.entry.line` means a sensitivity result can only ever hold a bare
text value - there is nowhere to record an S/I/R interpretation or a zone
diameter, and every specimen got the same 36-drug list regardless of whether the
drug is even reportable for that site.

## What this module ships

```
data/01_revenue_accounts.xml   24 income accounts, one per department (4011xx-4019xx)
data/02_departments.xml        27 departments in a two-level tree, with lab modality
data/03_tube_colors.xml        12 containers, sequenced in CLSI order of draw
data/04_sample_types.xml       15 specimen materials
data/05_methods_instruments.xml 18 methods + 11 analysers
data/06_antibiotics.xml        30 further agents, all class-sequenced
data/07_report_templates.xml   15 narrative templates (USG / Echo / ECG / DEXA / MRA)
data/08_retire_leih19_samples.xml  removes leih19's demo tests, adopts its Mantoux
data/10..34_*.xml              368 catalogue items with 722 components
```

Totals in a fresh database: **369 items, 722 components, 708 possible values**,
zero items without a department or revenue account.

## Design decisions

**Rates are provisional.** Every item carries the legacy rate in both `rate` and
`base_rate`. They are a starting point to be revised, not agreed pricing. Items
whose price is genuinely negotiated per case (surgeon team charge, implant,
machine charges) are seeded at 0 and flagged `manual`, so a missed pricing step
is visible rather than silently billing a stale figure.

**One revenue account per department.** `leih_accounting._income_account()` reads
the item's `accounts_id` first, so department-wise revenue falls out of the
general ledger with no extra reporting layer.

**Report layout is set per item, not guessed.** The six layouts leih19 supports
are assigned deliberately:

| Layout | Items | Used for |
|---|---|---|
| `tabular` | 192 | Test / Result / Unit / Reference grid - biochemistry, haematology, serology |
| `narrative` | 34 | USG, Echo, ECG, histopathology - prose plus measurements |
| `microbiology` | 16 | culture + organism + antibiogram |
| `special` | 7 | label/value forms - Mantoux, HLA-B27, GeneXpert, RT-PCR |
| `two_column` | 2 | Urine and Stool R/M/E - qualitative findings under headings |
| `transfusion` | 1 | cross matching with donor block and screening panel |

**Reference ranges drive auto-flagging.** 288 of 330 numeric components carry a
printed range, 268 carry `ref_low`/`ref_high` thresholds and 59 carry critical
thresholds. Results flag themselves H / L / HH / LL, and the printed report
picks the sex-specific range when the component defines one.

**Antibiograms use panels, not components.** Seven specimen-appropriate panels
(`tools/panels.py`) replace the flat 36-drug list: urinary agents on urine,
systemic and last-resort agents on blood, topicals on eye swabs, enteric agents
on stool.

**Conditional components.** 24 components appear only once a parent answer
warrants them - the organism and colony count on a culture stay hidden until the
technician records growth, so a no-growth report stays a two-line report.

## Editing the catalogue

The `data/1x_*.xml` .. `data/3x_*.xml` files are **generated**. Edit the spec and
rebuild:

```bash
cd legh-addons/leih_diagnostic_catalog
python3 tools/build_catalogue.py                      # regenerate the XML
python3 tools/reconcile.py ../../examination.entry\(1\).csv   # check nothing was lost
```

`tools/items/*.py` is where a test is defined - one readable line per component,
with reference ranges lining up in columns so they can be reviewed against a lab
manual. The builder refuses to run on a duplicate xmlid or a conditional
component pointing at a value its parent does not define.

The data files are `noupdate="1"`, so a module upgrade will not overwrite rates
or ranges edited in the UI. To re-apply the shipped values, uninstall and
reinstall the module.

## Audit trail

`docs/legacy_item_mapping.txt` maps all 396 legacy items to their new item and
records what happened to each. `docs/legacy_reconciliation.txt` is the summary.

Two legacy items were deliberately **not** carried forward:

- `Deprecated by IT (Electrolyte).` - marked deprecated in the source data.
- `LPH` - no test could be established from the name or its (absent) components.

Everything else is either carried forward or merged into a named survivor.
