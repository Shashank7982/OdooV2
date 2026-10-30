/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

const WORKFLOW_ACTIONS = new Set(["action_submit", "action_approve", "action_post"]);

patch(FormController.prototype, {
    async beforeExecuteActionButton(clickParams) {
        // Workflow methods perform their own permission and state checks.
        // Skip the generic pre-action save, which otherwise calls write()
        // and incorrectly blocks a read-only Finance Controller.
        if (WORKFLOW_ACTIONS.has(clickParams.name)) {
            return true;
        }
        return super.beforeExecuteActionButton(clickParams);
    },
});
