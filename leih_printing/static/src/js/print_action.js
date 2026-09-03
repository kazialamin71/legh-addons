/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

/**
 * "This computer" printing.
 *
 * The server hands us the finished PDF instead of a download URL. We drop it
 * into an off-screen iframe and call print() on it, so the browser's print
 * dialog opens straight over Odoo: no file saved, no extra tab, no navigating
 * away from the record.
 *
 * On a counter PC running `chrome.exe --kiosk-printing` there is no dialog at
 * all -- Chrome prints to that machine's default printer immediately. That is
 * what makes a USB printer on the desk work, which the server can never reach.
 *
 * The iframe must NOT be `display:none`. Chrome does not instantiate its PDF
 * viewer for a hidden frame, and printing a frame that was never laid out gives
 * a blank page -- the same trap as capturing a webcam frame too early.
 */

const PRINT_TIMEOUT = 60000;

function base64ToBlob(base64, type = "application/pdf") {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return new Blob([bytes], { type });
}

export function printPdfInBrowser(pdfBase64, name) {
    return new Promise((resolve, reject) => {
        let url;
        try {
            url = URL.createObjectURL(base64ToBlob(pdfBase64));
        } catch (err) {
            reject(err);
            return;
        }

        const iframe = document.createElement("iframe");
        iframe.title = name || "document";
        // Off-screen, but laid out and painted. See the note above.
        iframe.style.cssText =
            "position:fixed; right:0; bottom:0; width:1px; height:1px;" +
            "opacity:0; border:0; pointer-events:none;";
        iframe.src = url;

        let done = false;
        const cleanup = () => {
            if (done) {
                return;
            }
            done = true;
            clearTimeout(timer);
            // Firefox aborts the job if the frame goes away too soon, and the
            // print dialog is modal in some browsers and not in others, so the
            // frame outlives the call by a safe margin rather than a guess at
            // when the dialog closed.
            setTimeout(() => {
                URL.revokeObjectURL(url);
                iframe.remove();
            }, 60000);
        };

        const timer = setTimeout(() => {
            cleanup();
            reject(new Error("The PDF did not load in time."));
        }, PRINT_TIMEOUT);

        iframe.onload = () => {
            try {
                const frameWindow = iframe.contentWindow;
                frameWindow.focus();
                frameWindow.print();
                cleanup();
                resolve();
            } catch (err) {
                cleanup();
                reject(err);
            }
        };
        iframe.onerror = () => {
            cleanup();
            reject(new Error("The PDF could not be opened for printing."));
        };

        document.body.appendChild(iframe);
    });
}

/**
 * Registered as a *function* client action, not a Component: the action service
 * calls it and only navigates if it returns something, so printing happens over
 * the record the user is looking at rather than replacing it.
 *
 * It must be a real `ir.actions.client` rather than a custom action type --
 * `clean_action` on the server resolves `action.type` as a model name, so a
 * made-up type raises KeyError as soon as a report is launched from a button.
 */
registry.category("actions").add("leih_printing.print", async (env, action) => {
    const params = action.params || {};
    try {
        await printPdfInBrowser(params.pdf, params.name);
    } catch (err) {
        // Never leave the desk with nothing: if the browser would not print,
        // hand them the document anyway so the counter keeps moving.
        env.services.notification.add(
            _t(
                "This browser would not open the print dialog, so the document was downloaded instead."
            ),
            { type: "warning" }
        );
        const link = document.createElement("a");
        link.href = URL.createObjectURL(base64ToBlob(params.pdf));
        link.download = `${params.name || "document"}.pdf`;
        link.click();
        setTimeout(() => URL.revokeObjectURL(link.href), 60000);
    }
    if (params.close) {
        // Launched from a wizard that expects to close itself. Returning an
        // action is how a function client action asks for one more step.
        return { type: "ir.actions.act_window_close" };
    }
    // Nothing returned means "stay exactly where you are".
});
