/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { isBinarySize } from "@web/core/utils/binary";
import { url } from "@web/core/utils/urls";
import { Component, useRef, useState, onWillUnmount } from "@odoo/owl";

export class WebcamImageField extends Component {
    static template = "leih19.WebcamImageField";
    static props = { ...standardFieldProps };

    setup() {
        this.video = useRef("video");
        this.canvas = useRef("canvas");
        this.fileInput = useRef("fileInput");
        this.state = useState({ active: false });
        this.notification = useService("notification");
        this.stream = null;
        onWillUnmount(() => this.stop());
    }

    get value() {
        return this.props.record.data[this.props.name];
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

    async start() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            this.notification.add(
                "Webcam not available in this browser/context (needs HTTPS or localhost).",
                { type: "danger" }
            );
            return;
        }
        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: "user" },
            });
            this.state.active = true;
            await new Promise((r) => setTimeout(r, 0));
            if (this.video.el) {
                this.video.el.srcObject = this.stream;
                await this.video.el.play();
            }
        } catch (err) {
            this.notification.add(
                "Cannot access the webcam. Check camera permissions.",
                { type: "danger" }
            );
            this.stop();
        }
    }

    stop() {
        if (this.stream) {
            this.stream.getTracks().forEach((t) => t.stop());
            this.stream = null;
        }
        this.state.active = false;
    }

    async snap() {
        const video = this.video.el;
        const canvas = this.canvas.el;
        if (!video || !canvas) {
            return;
        }
        canvas.width = video.videoWidth || 320;
        canvas.height = video.videoHeight || 240;
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
