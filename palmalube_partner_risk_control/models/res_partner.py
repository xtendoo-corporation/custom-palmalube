# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    sale_block_on_overdue_invoice = fields.Boolean(
        string="Bloquear venta por impago",
        default=True,
        help="Si está activo, no se podrá vender a este cliente cuando tenga "
        "facturas vencidas pendientes de pago.",
    )
    sale_order_risk_allowed = fields.Boolean(
        string="Disponible para venta",
        compute="_compute_sale_order_risk_allowed",
        search="_search_sale_order_risk_allowed",
        help="Campo técnico usado para filtrar clientes bloqueados en ventas.",
    )
    pending_customer_invoice_count = fields.Integer(
        string="Facturas pendientes",
        compute="_compute_pending_customer_invoice_count",
    )

    @api.model
    def _get_pending_customer_invoice_domain(self, company=None, commercial_partners=None):
        company = company or self.env.company
        domain = [
            ("company_id", "=", company.id),
            ("move_type", "in", ("out_invoice", "out_receipt")),
            ("state", "=", "posted"),
            ("amount_residual", ">", 0),
            (
                "payment_state",
                "not in",
                ("paid", "reversed", "blocked", "invoicing_legacy"),
            ),
        ]
        if commercial_partners:
            domain.append(("partner_id", "child_of", commercial_partners.ids))
        return domain

    @api.model
    def _get_overdue_customer_invoice_domain(self, company=None, commercial_partners=None):
        company = company or self.env.company
        domain = [
            ("company_id", "=", company.id),
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("amount_residual", ">", 0),
            (
                "payment_state",
                "not in",
                ("in_payment", "paid", "reversed", "blocked", "invoicing_legacy"),
            ),
            ("invoice_date_due", "<", fields.Date.context_today(self)),
        ]
        if commercial_partners:
            domain.append(("partner_id", "child_of", commercial_partners.ids))
        return domain

    @api.model
    def _get_commercial_partners_with_overdue_invoices(self, company=None, partners=None):
        partners = partners or self.env["res.partner"]
        moves = self.env["account.move"].sudo().search(
            self._get_overdue_customer_invoice_domain(
                company=company,
                commercial_partners=partners.commercial_partner_id,
            )
        )
        return moves.mapped("partner_id.commercial_partner_id")

    def _has_overdue_unpaid_invoices(self, company=None):
        self.ensure_one()
        return self.commercial_partner_id in self._get_commercial_partners_with_overdue_invoices(
            company=company,
            partners=self,
        )

    def _is_sale_blocked_by_risk(self, company=None):
        self.ensure_one()
        return bool(
            self.sale_block_on_overdue_invoice
            and self._has_overdue_unpaid_invoices(company=company)
        )

    def _compute_sale_order_risk_allowed(self):
        blocked_partner_ids = set(
            self._get_commercial_partners_with_overdue_invoices(partners=self).ids
        )
        for partner in self:
            partner.sale_order_risk_allowed = not (
                partner.sale_block_on_overdue_invoice
                and partner.commercial_partner_id.id in blocked_partner_ids
            )

    def _compute_pending_customer_invoice_count(self):
        all_partners = self.with_context(active_test=False).search_fetch(
            [("id", "child_of", self.ids)],
            ["parent_id"],
        )
        invoice_groups = self.env["account.move"]._read_group(
            domain=[
                ("partner_id", "in", all_partners.ids),
                *self.env["account.move"]._check_company_domain(self.env.company),
                ("move_type", "in", ("out_invoice", "out_receipt")),
                ("state", "=", "posted"),
                ("amount_residual", ">", 0),
                ("payment_state", "not in", ("paid", "reversed", "blocked", "invoicing_legacy")),
            ],
            groupby=["partner_id"],
            aggregates=["__count"],
        )
        self_ids = set(self._ids)

        self.pending_customer_invoice_count = 0
        for partner, count in invoice_groups:
            while partner:
                if partner.id in self_ids:
                    partner.pending_customer_invoice_count += count
                partner = partner.parent_id

    def action_view_pending_customer_invoices(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action["name"] = "Facturas pendientes"
        action["domain"] = self._get_pending_customer_invoice_domain(
            company=self.env.company,
            commercial_partners=self,
        )
        action["context"] = {
            "default_move_type": "out_invoice",
            "move_type": "out_invoice",
            "journal_type": "sale",
            "search_default_unpaid": 1,
        }
        return action

    @api.model
    def _search_sale_order_risk_allowed(self, operator, value):
        if operator not in ("=", "!="):
            return []

        value = bool(value)
        search_allowed = (operator == "=" and value) or (operator == "!=" and not value)
        blocked_partner_ids = self._get_commercial_partners_with_overdue_invoices().ids

        if search_allowed:
            return [
                "|",
                ("sale_block_on_overdue_invoice", "=", False),
                ("commercial_partner_id", "not in", blocked_partner_ids),
            ]

        return [
            ("sale_block_on_overdue_invoice", "=", True),
            ("commercial_partner_id", "in", blocked_partner_ids),
        ]

