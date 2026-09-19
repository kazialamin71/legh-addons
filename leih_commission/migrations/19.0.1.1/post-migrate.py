"""Keep existing MOUs paying what they paid yesterday.

``_apply_excess_discount`` used to be gated on a non-zero
``overall_default_discount``:

    if self.deduct_from_discount and self.overall_default_discount:

so an MOU that allowed 0% discount -- the strictest setting there is -- had the
excess-discount deduction skipped entirely, and the referrer was paid in full
no matter how much was given away. The gate is gone, because a 0% allowance is
a real instruction and not an absent one.

That makes the switch bite on configurations where it never used to. A rule
that was written under the old behaviour never expressed a wish to deduct, so
the switch is turned off wherever it could not previously have had any effect,
leaving those MOUs computing exactly what they computed before. Anyone who
does want 0%-allowance deduction can tick it back on, and it will now work.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute("""
        UPDATE commission_configuration
           SET deduct_from_discount = FALSE
         WHERE deduct_from_discount
           AND COALESCE(overall_default_discount, 0) = 0
    """)
    if cr.rowcount:
        _logger.warning(
            "commission: 'Deduct Excess Discount From Commission' has been "
            "switched off on %s MOU(s) that allowed 0%% discount. The switch "
            "had no effect on them before and would now deduct every discount "
            "given; tick it back on where that is what you want.", cr.rowcount)
