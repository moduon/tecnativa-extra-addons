/** @odoo-module **/
/* Copyright 2023 Tecnativa - Carlos Roca
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl). */

import {useService} from "@web/core/utils/hooks";
import {registry} from "@web/core/registry";
import {FloatField} from "@web/views/fields/float/float_field";

export class FloatRiseUp extends FloatField {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }
    async _raiseUpValue() {
        this.props.record.update({[this.props.riseUpField]: this.props.value});
    }
}
FloatRiseUp.template = "sale_product_security_price.FloatRiseUp";
FloatRiseUp.props = {
    ...FloatField.props,
    riseUpField: {type: String},
};
FloatRiseUp.extractProps = ({attrs}) => {
    return {
        riseUpField: attrs.options.rise_up_field,
    };
};

registry.category("fields").add("rise_up", FloatRiseUp);
