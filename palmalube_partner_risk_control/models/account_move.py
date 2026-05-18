# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model
    def _is_partner_risk_control_applicable(self, move_type):
        return move_type == "out_invoice"

    @api.model
    def _get_partner_risk_block_message(self, partner):
        return _(
            "No se puede facturar por impago de factura. "
            "El cliente %(partner_name)s tiene facturas vencidas sin pagar.",
            partner_name=partner.display_name,
        )

    @api.model
    def _raise_if_partner_is_blocked(self, partner, move_type, company=None):
        if (
            self._is_partner_risk_control_applicable(move_type)
            and partner
            and partner._is_sale_blocked_by_risk(company=company)
        ):
            raise ValidationError(self._get_partner_risk_block_message(partner))

    @api.onchange("partner_id")
    def _onchange_partner_id_risk_control(self):
        move_type = self.move_type or self.env.context.get("default_move_type")
        if (
            self._is_partner_risk_control_applicable(move_type)
            and self.partner_id
            and self.partner_id._is_sale_blocked_by_risk(company=self.company_id)
        ):
            blocked_partner = self.partner_id
            self.partner_id = False
            self.partner_shipping_id = False
            return {
                "warning": {
                    "title": _("Cliente bloqueado"),
                    "message": self._get_partner_risk_block_message(blocked_partner),
                }
            }
        return {}

    @api.model_create_multi
    def create(self, vals_list):
        companies = self.env["res.company"].browse(
            [vals["company_id"] for vals in vals_list if vals.get("company_id")]
        )
        company_by_id = {company.id: company for company in companies}
        default_move_type = self.env.context.get("default_move_type") or "entry"

        for vals in vals_list:
            partner_id = vals.get("partner_id")
            if not partner_id:
                continue

            move_type = vals.get("move_type") or default_move_type
            company = company_by_id.get(vals.get("company_id")) or self.env.company
            partner = self.env["res.partner"].browse(partner_id)
            self._raise_if_partner_is_blocked(
                partner,
                move_type=move_type,
                company=company,
            )

        return super().create(vals_list)

    def write(self, vals):
        partner_in_vals = "partner_id" in vals
        company_in_vals = "company_id" in vals
        move_type_in_vals = "move_type" in vals

        partner = (
            self.env["res.partner"].browse(vals["partner_id"])
            if vals.get("partner_id")
            else False
        )
        company = (
            self.env["res.company"].browse(vals["company_id"])
            if vals.get("company_id")
            else False
        )

        if partner_in_vals or company_in_vals or move_type_in_vals:
            for move in self:
                target_move_type = vals.get("move_type") or move.move_type
                if not self._is_partner_risk_control_applicable(target_move_type):
                    continue

                target_partner = partner if partner_in_vals else move.partner_id
                target_company = company or move.company_id
                self._raise_if_partner_is_blocked(
                    target_partner,
                    move_type=target_move_type,
                    company=target_company,
                )

        return super().write(vals)

    def action_post(self):
        for move in self:
            self._raise_if_partner_is_blocked(
                move.partner_id,
                move_type=move.move_type,
                company=move.company_id,
            )
        return super().action_post()

