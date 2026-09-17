/**
 * Generic-name search in the POS.
 *
 * A customer asks for "paracetamol" and the shelf holds Napa, Ace and Xpa, so
 * the search box has to match the molecule as well as the brand. Two places
 * need it: the in-memory filter over the products already loaded in the
 * session, and the database fallback the cashier reaches by pressing Enter when
 * the session's own list has nothing.
 */
import { patch } from "@web/core/utils/patch";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";
import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

function withGeneric(base, generic) {
    return generic ? `${base} ${generic}` : base;
}

patch(ProductTemplate.prototype, {
    get searchString() {
        return withGeneric(super.searchString, this.medicine_generic_name);
    },
});

patch(ProductProduct.prototype, {
    get searchString() {
        return withGeneric(super.searchString, this.medicine_generic_name);
    },
});

patch(ProductScreen.prototype, {
    loadProductFromDBDomain(searchProductWord) {
        const domain = super.loadProductFromDBDomain(searchProductWord);
        // The base domain is a flat prefix-notation OR chain ending in the two
        // mandatory filters. Splice the generic in before those so it joins the
        // OR rather than replacing the "available in POS" guard.
        const guards = domain.splice(-2, 2);
        return [
            "|",
            ...domain,
            ["medicine_generic_name", "ilike", searchProductWord],
            ...guards,
        ];
    },
});
