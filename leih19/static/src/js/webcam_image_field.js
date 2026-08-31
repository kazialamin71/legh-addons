/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { isBinarySize } from "@web/core/utils/binary";
import { url } from "@web/core/utils/urls";
import { Component, useRef, useState, useEffect, onWillUnmount } from "@odoo/owl";

/**
 * Image field with live webcam capture.
 *
 * The awkward part is not the capture, it is where this runs. Browsers gate
 * `getUserMedia` behind a *secure context*: https, or localhost. This server is
 * reached over plain http from every other desk in the hospital, so on those
 * machines `navigator.mediaDevices` is simply `undefined` -- there is no
 * permission prompt to accept and nothing the server can send that changes it.
 * It is a client-side rule and only the client can lift it.
 *
 * So the widget does three things instead of failing with a shrug:
 *
 *  1. detects the situation up front, rather than throwing at click time;
 *  2. shows the operator the exact one-time browser setting that whitelists
 *     *this* origin, so a desk can fix itself without calling anyone;
 *  3. offers "Take Photo", a file input with `capture`, which hands off to the
 *     device's own camera app. That is not `getUserMedia` and is not gated, so
 *     it works over plain http today on every phone and tablet -- which is what
 *     most of the arrival desks actually have.
 *
 * Plain "Upload" is always available as the last resort.
 */
export class WebcamImageField extends Component {
    static template = "leih19.WebcamImageField";
    static props = { ...standardFieldProps };

    setup() {
        this.video = useRef("video");
        this.canvas = useRef("canvas");
        this.fileInput = useRef("fileInput");
        this.captureInput = useRef("captureInput");
        this.state = useState({
            active: false,
            // Frames are actually arriving. Until then Capture is disabled --
            // grabbing early is what produced a black photo.
            ready: false,
            help: false,
            // Desk webcams face the patient, but a tablet's default camera is
            // the selfie one -- which would photograph the operator.
            facingMode: "user",
            hasMultipleCameras: false,
        });
        this.notification = useService("notification");
        this.stream = null;

        // The stream must be attached *after* Owl has rendered the <video>,
        // which is what useEffect guarantees. Assigning it straight after
        // `state.active = true` raced the render: `this.video.el` was still
        // null, so the element got no stream and stayed black.
        useEffect(
            (active) => {
                if (!active || !this.stream || !this.video.el) {
                    return;
                }
                const video = this.video.el;
                let cancelled = false;
                video.srcObject = this.stream;

                const onPlaying = () => {
                    if (!cancelled) {
                        this.state.ready = true;
                    }
                };
                const onMeta = async () => {
                    if (cancelled) {
                        return;
                    }
                    try {
                        await video.play();
                    } catch (err) {
                        // Autoplay policy. The element is muted and playsinline
                        // so this is rare, but never let it throw unhandled.
                        this.notification.add(
                            "The browser would not start the camera preview. Click the video and try again.",
                            { type: "warning" }
                        );
                    }
                };

                video.addEventListener("playing", onPlaying);
                if (video.readyState >= 1 /* HAVE_METADATA */) {
                    onMeta();
                } else {
                    video.addEventListener("loadedmetadata", onMeta, { once: true });
                }

                return () => {
                    cancelled = true;
                    video.removeEventListener("playing", onPlaying);
                    video.removeEventListener("loadedmetadata", onMeta);
                    video.srcObject = null;
                };
            },
            () => [this.state.active]
        );

        onWillUnmount(() => this.stop());
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get readonly() {
        return this.props.readonly;
    }

    get imageSrc() {
        const v = this.value;
        if (!v) {
            return false;
        }
        if (typeof v === "string" && v.startsWith("data:")) {
            return v;
        }
        // Saved record: the field holds a binary-size placeholder -> serve via URL.
        if (isBinarySize(v)) {
            return url("/web/image", {
                model: this.props.record.resModel,
                id: this.props.record.resId,
                field: this.props.name,
                unique: this.props.record.data.write_date,
            });
        }
        // Freshly captured/uploaded base64.
        return "data:image/png;base64," + v;
    }

    // ------------------------------------------------------------------
    // What this browser, on this origin, is actually allowed to do
    // ------------------------------------------------------------------
    get cameraSupported() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }

    /** True when the page is plain http on something that is not localhost. */
    get insecureOrigin() {
        return !window.isSecureContext && window.location.protocol === "http:";
    }

    get origin() {
        return window.location.origin;
    }

    toggleHelp() {
        this.state.help = !this.state.help;
    }

    async start() {
        if (!this.cameraSupported) {
            // Don't bury this in a toast that disappears: the operator needs the
            // steps in front of them while they follow along.
            this.state.help = true;
            return;
        }
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                // `ideal`, not `exact`: a desk webcam has no facing mode at all,
                // and an exact constraint makes such a camera fail outright
                // instead of just being used as-is.
                video: {
                    facingMode: { ideal: this.state.facingMode },
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                },
            });
            this.state.ready = false;
            this.state.help = false;
            // The useEffect above attaches the stream once <video> exists.
            this.state.active = true;
            // Only worth offering a flip button when there is something to flip to.
            if (navigator.mediaDevices.enumerateDevices) {
                const devices = await navigator.mediaDevices.enumerateDevices();
                this.state.hasMultipleCameras =
                    devices.filter((d) => d.kind === "videoinput").length > 1;
            }
        } catch (err) {
            this.stop();
            this.notification.add(this._cameraErrorMessage(err), { type: "danger" });
            if (err && err.name === "NotAllowedError") {
                // Chrome reports a blocked insecure origin the same way it
                // reports a denied prompt, so show the whitelist steps too.
                this.state.help = true;
            }
        }
    }

    _cameraErrorMessage(err) {
        switch (err && err.name) {
            case "NotAllowedError":
                return "The browser blocked the camera. Allow camera access for this site, then try again.";
            case "NotFoundError":
            case "OverconstrainedError":
                return "No camera was found on this device. Use Take Photo or Upload instead.";
            case "NotReadableError":
                return "The camera is already in use by another application.";
            default:
                return "Cannot access the camera. Use Take Photo or Upload instead.";
        }
    }

    stop() {
        if (this.stream) {
            this.stream.getTracks().forEach((t) => t.stop());
            this.stream = null;
        }
        this.state.active = false;
        this.state.ready = false;
    }

    async flip() {
        this.state.facingMode = this.state.facingMode === "user" ? "environment" : "user";
        this.stop();
        await this.start();
    }

    /** Resolve once the element actually holds a frame worth drawing. */
    async _waitForFrame(video, timeout = 3000) {
        const deadline = Date.now() + timeout;
        while (Date.now() < deadline) {
            if (video.readyState >= 2 /* HAVE_CURRENT_DATA */ && video.videoWidth > 0) {
                return true;
            }
            await new Promise((resolve) => requestAnimationFrame(resolve));
        }
        return video.readyState >= 2 && video.videoWidth > 0;
    }

    async snap() {
        const video = this.video.el;
        const canvas = this.canvas.el;
        if (!video || !canvas) {
            return;
        }
        // Without this the canvas is sized 320x240 from the `||` fallbacks and
        // drawImage paints nothing -- a perfectly black photo, which is exactly
        // what a camera that has not delivered its first frame yet produces.
        if (!(await this._waitForFrame(video))) {
            this.notification.add(
                "The camera has not produced a picture yet. Give it a moment and press Capture again.",
                { type: "warning" }
            );
            return;
        }
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
        const dataUrl = canvas.toDataURL("image/jpeg", 0.9);
        await this.props.record.update({ [this.props.name]: dataUrl.split(",")[1] });
        this.stop();
    }

    triggerUpload() {
        if (this.fileInput.el) {
            this.fileInput.el.click();
        }
    }

    /** Hand off to the device's own camera app -- not gated by secure context. */
    triggerDeviceCamera() {
        if (this.captureInput.el) {
            this.captureInput.el.click();
        }
    }

    onFileChange(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) {
            return;
        }
        const reader = new FileReader();
        reader.onload = () => {
            const b64 = String(reader.result).split(",")[1];
            this.props.record.update({ [this.props.name]: b64 });
        };
        reader.readAsDataURL(file);
        // Let the same file be picked again after a Remove.
        ev.target.value = "";
    }

    clear() {
        this.props.record.update({ [this.props.name]: false });
    }
}

export const webcamImageField = {
    component: WebcamImageField,
    displayName: "Webcam Image",
    supportedTypes: ["binary"],
};

registry.category("fields").add("image_webcam", webcamImageField);
