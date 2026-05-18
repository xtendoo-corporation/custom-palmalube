# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class TestPartnerRiskControl(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner_model = cls.env["res.partner"]
        cls.sale_order_model = cls.env["sale.order"]
        cls.maintenance_request_model = cls.env["maintenance.request"]
        cls.account_move_model = cls.env["account.move"]

        cls.maintenance_team = cls.env["maintenance.team"].search(
            [("company_id", "=", cls.company.id)],
            limit=1,
        )
        if not cls.maintenance_team:
            cls.maintenance_team = cls.env["maintenance.team"].create({
                "name": "Equipo mantenimiento test",
                "company_id": cls.company.id,
            })

        cls.sale_journal = cls.env["account.journal"].search(
            [
                ("type", "=", "sale"),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        if not cls.sale_journal:
            cls.sale_journal = cls.env["account.journal"].create({
                "name": "Diario ventas test",
                "code": "SVT1",
                "type": "sale",
                "company_id": cls.company.id,
            })

        cls.income_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "income"),
            ],
            limit=1,
        )
        if not cls.income_account:
            cls.income_account = cls.env["account.account"].create({
                "name": "Cuenta ingresos test",
                "code": "TEST7000",
                "account_type": "income",
            })
        cls.receivable_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "asset_receivable"),
            ],
            limit=1,
        )
        if not cls.receivable_account:
            cls.receivable_account = cls.env["account.account"].create({
                "name": "Cuenta cobro test",
                "code": "TEST4300",
                "account_type": "asset_receivable",
                "reconcile": True,
            })

        cls.partner_ok = cls.partner_model.create({
            "name": "Cliente permitido",
            "customer_rank": 1,
            "property_account_receivable_id": cls.receivable_account.id,
        })
        cls.partner_blocked = cls.partner_model.create({
            "name": "Cliente bloqueado",
            "customer_rank": 1,
            "property_account_receivable_id": cls.receivable_account.id,
        })

        cls._create_overdue_invoice(cls.partner_blocked)

    @classmethod
    def _create_overdue_invoice(cls, partner):
        invoice = cls.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "journal_id": cls.sale_journal.id,
            "invoice_date": fields.Date.today() - timedelta(days=10),
            "invoice_date_due": fields.Date.today() - timedelta(days=5),
            "invoice_line_ids": [
                Command.create({
                    "name": "Línea test",
                    "quantity": 1,
                    "price_unit": 100,
                    "account_id": cls.income_account.id,
                })
            ],
        })
        invoice.action_post()
        return invoice

    def _get_maintenance_request_vals(self, **extra_vals):
        vals = {
            "name": "Solicitud test",
            "company_id": self.company.id,
            "maintenance_team_id": self.maintenance_team.id,
        }
        vals.update(extra_vals)
        return vals

    def _get_customer_invoice_vals(self, **extra_vals):
        vals = {
            "move_type": "out_invoice",
            "partner_id": self.partner_ok.id,
            "company_id": self.company.id,
            "journal_id": self.sale_journal.id,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [
                Command.create({
                    "name": "Línea factura test",
                    "quantity": 1,
                    "price_unit": 100,
                    "account_id": self.income_account.id,
                })
            ],
        }
        vals.update(extra_vals)
        return vals

    def test_01_partner_risk_detection(self):
        self.assertFalse(
            self.partner_ok._is_sale_blocked_by_risk(company=self.company)
        )
        self.assertTrue(
            self.partner_blocked._is_sale_blocked_by_risk(company=self.company)
        )

    def test_02_pending_invoice_button(self):
        self.assertEqual(self.partner_blocked.pending_customer_invoice_count, 1)

        action = self.partner_blocked.action_view_pending_customer_invoices()
        invoices = self.env["account.move"].search(action["domain"])

        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices.partner_id, self.partner_blocked)

    def test_03_onchange_clears_blocked_partner(self):
        order = self.sale_order_model.new({
            "company_id": self.company.id,
            "partner_id": self.partner_blocked.id,
        })

        warning = order._onchange_partner_id_risk_control()

        self.assertFalse(order.partner_id)
        self.assertEqual(warning["warning"]["title"], "Cliente bloqueado")
        self.assertIn("No se le puede vender por impago de factura", warning["warning"]["message"])

    def test_04_create_order_with_blocked_partner_raises(self):
        with self.assertRaises(ValidationError):
            self.sale_order_model.create({
                "partner_id": self.partner_blocked.id,
                "company_id": self.company.id,
            })

    def test_05_create_order_allowed_when_control_disabled(self):
        self.partner_blocked.sale_block_on_overdue_invoice = False

        order = self.sale_order_model.create({
            "partner_id": self.partner_blocked.id,
            "company_id": self.company.id,
        })

        self.assertEqual(order.partner_id, self.partner_blocked)

    def test_06_confirmation_is_blocked_if_partner_turns_overdue(self):
        order = self.sale_order_model.create({
            "partner_id": self.partner_ok.id,
            "company_id": self.company.id,
        })
        self._create_overdue_invoice(self.partner_ok)

        with self.assertRaises(UserError):
            order.action_confirm()

    def test_07_maintenance_onchange_clears_blocked_partner(self):
        request = self.maintenance_request_model.new(
            self._get_maintenance_request_vals(partner_id=self.partner_blocked.id)
        )

        warning = request._onchange_partner_id_risk_control()

        self.assertFalse(request.partner_id)
        self.assertEqual(warning["warning"]["title"], "Cliente bloqueado")
        self.assertIn(
            "No se puede asignar el cliente por impago de factura",
            warning["warning"]["message"],
        )

    def test_08_create_maintenance_with_blocked_partner_raises(self):
        with self.assertRaises(ValidationError):
            self.maintenance_request_model.create(
                self._get_maintenance_request_vals(partner_id=self.partner_blocked.id)
            )

    def test_09_write_maintenance_with_blocked_partner_raises(self):
        request = self.maintenance_request_model.create(
            self._get_maintenance_request_vals(partner_id=self.partner_ok.id)
        )

        with self.assertRaises(ValidationError):
            request.write({"partner_id": self.partner_blocked.id})

    def test_10_create_maintenance_allowed_when_control_disabled(self):
        self.partner_blocked.sale_block_on_overdue_invoice = False

        request = self.maintenance_request_model.create(
            self._get_maintenance_request_vals(partner_id=self.partner_blocked.id)
        )

        self.assertEqual(request.partner_id, self.partner_blocked)

    def test_11_invoice_onchange_clears_blocked_partner(self):
        invoice = self.account_move_model.new(
            self._get_customer_invoice_vals(partner_id=self.partner_blocked.id)
        )

        warning = invoice._onchange_partner_id_risk_control()

        self.assertFalse(invoice.partner_id)
        self.assertEqual(warning["warning"]["title"], "Cliente bloqueado")
        self.assertIn(
            "No se puede facturar por impago de factura",
            warning["warning"]["message"],
        )

    def test_12_create_customer_invoice_with_blocked_partner_raises(self):
        with self.assertRaises(ValidationError):
            self.account_move_model.create(
                self._get_customer_invoice_vals(partner_id=self.partner_blocked.id)
            )

    def test_13_post_customer_invoice_is_blocked_if_partner_turns_overdue(self):
        invoice = self.account_move_model.create(
            self._get_customer_invoice_vals(partner_id=self.partner_ok.id)
        )
        self._create_overdue_invoice(self.partner_ok)

        with self.assertRaises(ValidationError):
            invoice.action_post()

    def test_14_customer_receipt_is_not_blocked(self):
        receipt = self.account_move_model.create(
            self._get_customer_invoice_vals(
                move_type="out_receipt",
                partner_id=self.partner_blocked.id,
            )
        )

        self.assertEqual(receipt.partner_id, self.partner_blocked)

