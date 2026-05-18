# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def _get_partner_risk_block_message(self, partner):
        return _(
            "No se le puede vender por impago de factura. "
            "El cliente %(partner_name)s tiene facturas vencidas sin pagar.",
            partner_name=partner.display_name,
        )

    @api.model
    def _raise_if_partner_is_blocked(self, partner, company=None):
        if partner and partner._is_sale_blocked_by_risk(company=company):
            raise ValidationError(self._get_partner_risk_block_message(partner))

    @api.onchange("partner_id")
    def _onchange_partner_id_risk_control(self):
        if self.partner_id and self.partner_id._is_sale_blocked_by_risk(
            company=self.company_id
        ):
            blocked_partner = self.partner_id
            self.partner_id = False
            self.partner_invoice_id = False
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
        for vals in vals_list:
            partner_id = vals.get("partner_id")
            if not partner_id:
                continue
            partner = self.env["res.partner"].browse(partner_id)
            company = company_by_id.get(vals.get("company_id")) or self.env.company
            self._raise_if_partner_is_blocked(partner, company=company)
        return super().create(vals_list)

    def write(self, vals):
        partner = self.env["res.partner"].browse(vals["partner_id"]) if vals.get("partner_id") else False
        company = self.env["res.company"].browse(vals["company_id"]) if vals.get("company_id") else False

        if partner or company:
            for order in self:
                target_partner = partner or order.partner_id
                target_company = company or order.company_id
                self._raise_if_partner_is_blocked(target_partner, company=target_company)

        return super().write(vals)

    def _confirmation_error_message(self):
        message = super()._confirmation_error_message()
        if message:
            return message
        self.ensure_one()
        if self.partner_id._is_sale_blocked_by_risk(company=self.company_id):
            return self._get_partner_risk_block_message(self.partner_id)
        return False

