/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useInputField } from "@web/views/fields/input_field_hook";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

/**
 * 12-hour clock entry for the Float fields that hold a time of day.
 *
 * Odoo has no time-of-day field, so those times are Floats (hours since
 * midnight) and the stock `float_time` widget shows and parses them as a
 * 24-hour HH:MM. Nobody at an OPD counter thinks in 24-hour time: the doctor's
 * board says "5:00 PM", the patient says "five", and the desk then has to do
 * the conversion in its head and type 17:00. This widget removes that step --
 * it reads and writes the same Float, but in the clock the desk is looking at.
 *
 * Entry is deliberately forgiving, because it is typed fast between two
 * sentences: "5pm", "5 PM", "5:30 pm", "530p", "1730" and "17:30" all land on
 * the same value. A time typed with no AM/PM is read as a 24-hour clock, so the
 * habits of anyone used to `float_time` keep working unchanged.
 */

/**
 * Render a Float as `hh:mm AM`.
 *
 * Falsy counts as "not set". A Float column has no NULL, so 0.0 is both
 * "midnight" and "never filled in" -- and since every new record starts at 0.0,
 * showing it as "12:00 AM" would put a time on every blank form. Midnight is
 * not a time an OPD books, so the blank wins. This matches
 * `appointment.booking.time_display`, which prints the same way.
 *
 * @param {number|false} value hours since midnight
 * @returns {string}
 */
export function formatTime12(value) {
    if (!value) {
        return "";
    }
    let hours = Math.floor(value);
    let minutes = Math.round((value - hours) * 60);
    if (minutes === 60) {
        minutes = 0;
        hours += 1;
    }
    hours %= 24;
    return `${String(hours % 12 || 12).padStart(2, "0")}:${String(minutes).padStart(2, "0")} ${
        hours < 12 ? "AM" : "PM"
    }`;
}

/**
 * Read a typed clock time back into hours since midnight.
 *
 * @param {string} value
 * @returns {number}
 * @throws {Error} when the text is not a time, which is what makes
 *   `useInputField` mark the field invalid instead of silently storing a 0.
 */
export function parseTime12(value) {
    let text = String(value ?? "")
        .trim()
        .toUpperCase();
    if (!text) {
        return 0;
    }

    // Trailing meridiem, in every shape a desk actually types it: "PM", "P.M.",
    // "p", and with or without a space in front.
    let meridiem = null;
    const suffix = text.match(/([AP])\.?\s*M?\.?$/);
    if (suffix) {
        meridiem = suffix[1];
        text = text.slice(0, suffix.index).trim();
    }

    let hours;
    let minutes;
    if (/[:.]/.test(text)) {
        const [rawHours, rawMinutes = "0"] = text.split(/[:.]/);
        hours = parseInt(rawHours, 10);
        minutes = parseInt(rawMinutes, 10);
    } else {
        // No separator: "5" is an hour, "530" and "1730" are hour + minutes.
        const digits = text.replace(/\D/g, "");
        if (digits !== text || digits.length > 4) {
            throw new Error(`"${value}" is not a time`);
        }
        if (digits.length <= 2) {
            hours = parseInt(digits, 10);
            minutes = 0;
        } else {
            hours = parseInt(digits.slice(0, -2), 10);
            minutes = parseInt(digits.slice(-2), 10);
        }
    }

    if (!Number.isInteger(hours) || !Number.isInteger(minutes) || minutes > 59) {
        throw new Error(`"${value}" is not a time`);
    }
    if (meridiem) {
        if (hours < 1 || hours > 12) {
            throw new Error(`"${value}" is not a 12-hour clock time`);
        }
        hours = (hours % 12) + (meridiem === "P" ? 12 : 0);
    } else if (hours > 23) {
        throw new Error(`"${value}" is not a time`);
    }
    return hours + minutes / 60;
}

export class FloatTime12Field extends Component {
    static template = "leih19.FloatTime12Field";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };

    setup() {
        useInputField({
            getValue: () => this.formattedValue,
            parse: (v) => parseTime12(v),
        });
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get formattedValue() {
        return formatTime12(this.value);
    }

    get meridiem() {
        return this.value && Math.floor(this.value) % 24 >= 12 ? "PM" : "AM";
    }

    /**
     * Flip AM <-> PM without retyping. `tabindex=-1` on the button keeps it out
     * of the keyboard path: a desk working down the form with Tab alone should
     * never land here, it types the meridiem as part of the time.
     *
     * Clicking blurs the input first, so `useInputField` has already committed
     * whatever was being typed by the time this runs.
     */
    toggleMeridiem() {
        const value = this.value;
        if (!value) {
            return;
        }
        const hours = Math.floor(value) % 24;
        this.props.record.update({
            [this.props.name]: hours < 12 ? value + 12 : value - 12,
        });
    }
}

export const floatTime12Field = {
    component: FloatTime12Field,
    displayName: _t("Time (12-hour)"),
    supportedTypes: ["float"],
    // A blank time still has to show its input, otherwise the form renders an
    // empty span the desk cannot click into.
    isEmpty: () => false,
    extractProps: ({ placeholder }) => ({ placeholder }),
};

registry.category("fields").add("float_time_12h", floatTime12Field);
