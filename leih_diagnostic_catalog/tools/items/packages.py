"""Health checkup packages.

Priced as one item; the constituent tests are listed in the name so the
counter can explain what is covered. Once ``examine.package`` is configured
these should be linked to their component tests there, which is what drives
automatic result creation for each test in the package.
"""

from catalogue_spec import ITEM
from refs import AC_PACKAGE, PACKAGE

ITEMS = [
    ITEM('Basic Health Checkup Package', PACKAGE, AC_PACKAGE, 3000,
         xmlid='pkg_basic_health_checkup', group='other', sample_req=True,
         tube='tube_gold_sst',
         components=[]),
    ITEM('Executive Health Checkup Package', PACKAGE, AC_PACKAGE, 4500,
         xmlid='pkg_executive_health_checkup', group='other', sample_req=True,
         tube='tube_gold_sst',
         components=[]),
]
