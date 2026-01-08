# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestImportInvoiceWizard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Empresa
        cls.company = cls.env.company

        # Moneda
        cls.currency_eur = cls.env.ref("base.EUR")

        # Diario de compras
        cls.journal_purchase = cls.env["account.journal"].search(
            [
                ("type", "=", "purchase"),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        if not cls.journal_purchase:
            cls.journal_purchase = cls.env["account.journal"].create({
                "name": "Purchase Journal Test",
                "code": "PTEST",
                "type": "purchase",
                "company_id": cls.company.id,
            })

        # Cuentas contables
        cls.account_expense = cls.env["account.account"].search(
            [
                ("account_type", "=", "expense"),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        if not cls.account_expense:
            cls.account_expense = cls.env["account.account"].create({
                "name": "Test Expense Account",
                "code": "600000TEST",
                "account_type": "expense",
                "company_id": cls.company.id,
            })

        cls.account_tax = cls.env["account.account"].search(
            [
                ("account_type", "=", "asset_current"),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        if not cls.account_tax:
            cls.account_tax = cls.env["account.account"].create({
                "name": "Test Tax Account",
                "code": "472000TEST",
                "account_type": "asset_current",
                "company_id": cls.company.id,
            })

        cls.account_payable = cls.env["account.account"].search(
            [
                ("account_type", "=", "liability_payable"),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        if not cls.account_payable:
            cls.account_payable = cls.env["account.account"].create({
                "name": "Test Payable Account",
                "code": "400000TEST",
                "account_type": "liability_payable",
                "company_id": cls.company.id,
            })

        # Proveedor de prueba
        cls.partner_test = cls.env["res.partner"].create({
            "name": "Test Supplier",
            "supplier_rank": 1,
            "property_account_payable_id": cls.account_payable.id,
        })

    def _create_wizard(self, csv_content, dry_run=False):
        """Helper para crear wizard con CSV."""
        csv_b64 = base64.b64encode(csv_content.encode("utf-8"))

        wizard = self.env["import.invoice.wizard"].create({
            "csv_file": csv_b64,
            "csv_filename": "test.csv",
            "company_id": self.company.id,
            "journal_id": self.journal_purchase.id,
            "expense_account_id": self.account_expense.id,
            "tax_account_id": self.account_tax.id,
            "payable_account_id": self.account_payable.id,
            "create_partners": True,
            "dry_run": dry_run,
        })

        return wizard

    def test_01_import_partner_with_comma_no_quotes(self):
        """Test: importar partner con coma SIN comillas."""
        csv_content = """move_type,name,invoice_date,partner_name,amount_untaxed,amount_tax,amount_total,state,currency_id
out_invoice,ST001,2025-12-30,RYME WORLDWIDE, S.A.,221.50,0.00,221.50,draft,EUR"""

        wizard = self._create_wizard(csv_content)
        wizard.action_import_invoices()

        # Verificar que se creó la factura
        self.assertEqual(wizard.created_count, 1)
        self.assertEqual(wizard.error_count, 0)

        # Buscar la factura creada
        invoice = self.env["account.move"].search([
            ("ref", "=", "ST001"),
            ("company_id", "=", self.company.id),
        ])

        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.move_type, "in_invoice")
        self.assertEqual(invoice.partner_id.name, "RYME WORLDWIDE, S.A.")

        # Verificar importes exactos
        self.assertAlmostEqual(invoice.amount_untaxed, 221.50, places=2)
        self.assertAlmostEqual(invoice.amount_tax, 0.00, places=2)
        self.assertAlmostEqual(invoice.amount_total, 221.50, places=2)

    def test_02_import_partner_with_comma_and_quotes(self):
        """Test: importar partner entrecomillado con coma."""
        csv_content = """move_type,name,invoice_date,partner_name,amount_untaxed,amount_tax,amount_total,state,currency_id
out_invoice,ST002,2025-12-30,"S.P. AUTO REISEN, S.L.",547.40,38.32,585.72,draft,EUR"""

        wizard = self._create_wizard(csv_content)
        wizard.action_import_invoices()

        # Verificar creación
        self.assertEqual(wizard.created_count, 1)
        self.assertEqual(wizard.error_count, 0)

        # Buscar factura
        invoice = self.env["account.move"].search([
            ("ref", "=", "ST002"),
            ("company_id", "=", self.company.id),
        ])

        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.move_type, "in_invoice")
        self.assertEqual(invoice.partner_id.name, "S.P. AUTO REISEN, S.L.")

        # Verificar importes
        self.assertAlmostEqual(invoice.amount_untaxed, 547.40, places=2)
        self.assertAlmostEqual(invoice.amount_tax, 38.32, places=2)
        self.assertAlmostEqual(invoice.amount_total, 585.72, places=2)

    def test_03_import_negative_amounts_creates_refund(self):
        """Test: importar con importes negativos crea in_refund."""
        csv_content = """move_type,name,invoice_date,partner_name,amount_untaxed,amount_tax,amount_total,state,currency_id
out_invoice,ST003,2025-12-30,Test Supplier,-100.00,-21.00,-121.00,draft,EUR"""

        wizard = self._create_wizard(csv_content)
        wizard.action_import_invoices()

        # Verificar creación
        self.assertEqual(wizard.created_count, 1)
        self.assertEqual(wizard.error_count, 0)

        # Buscar factura
        invoice = self.env["account.move"].search([
            ("ref", "=", "ST003"),
            ("company_id", "=", self.company.id),
        ])

        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.move_type, "in_refund")

        # Verificar importes (en refund Odoo los muestra positivos)
        self.assertAlmostEqual(invoice.amount_untaxed, 100.00, places=2)
        self.assertAlmostEqual(invoice.amount_tax, 21.00, places=2)
        self.assertAlmostEqual(invoice.amount_total, 121.00, places=2)

    def test_04_duplicate_detection(self):
        """Test: detectar duplicados."""
        csv_content = """move_type,name,invoice_date,partner_name,amount_untaxed,amount_tax,amount_total,state,currency_id
out_invoice,ST004,2025-12-30,Test Supplier,100.00,21.00,121.00,draft,EUR
out_invoice,ST004,2025-12-30,Test Supplier,100.00,21.00,121.00,draft,EUR"""

        wizard = self._create_wizard(csv_content)
        wizard.action_import_invoices()

        # Primera debe crearse, segunda debe saltar
        self.assertEqual(wizard.created_count, 1)
        self.assertEqual(wizard.skipped_count, 1)
        self.assertEqual(wizard.error_count, 0)

    def test_05_dry_run_mode(self):
        """Test: modo simulación no crea facturas."""
        csv_content = """move_type,name,invoice_date,partner_name,amount_untaxed,amount_tax,amount_total,state,currency_id
out_invoice,ST005,2025-12-30,Test Supplier,100.00,21.00,121.00,draft,EUR"""

        wizard = self._create_wizard(csv_content, dry_run=True)

        # Contar facturas antes
        count_before = self.env["account.move"].search_count([
            ("company_id", "=", self.company.id),
        ])

        wizard.action_import_invoices()

        # Contar facturas después
        count_after = self.env["account.move"].search_count([
            ("company_id", "=", self.company.id),
        ])

        # No debe haber creado ninguna
        self.assertEqual(count_before, count_after)

    def test_06_invalid_currency(self):
        """Test: moneda inválida genera error."""
        csv_content = """move_type,name,invoice_date,partner_name,amount_untaxed,amount_tax,amount_total,state,currency_id
out_invoice,ST006,2025-12-30,Test Supplier,100.00,21.00,121.00,draft,XXX"""

        wizard = self._create_wizard(csv_content)
        wizard.action_import_invoices()

        # Debe generar error
        self.assertEqual(wizard.created_count, 0)
        self.assertEqual(wizard.error_count, 1)

    def test_07_amounts_dont_match(self):
        """Test: importes que no cuadran generan error."""
        csv_content = """move_type,name,invoice_date,partner_name,amount_untaxed,amount_tax,amount_total,state,currency_id
out_invoice,ST007,2025-12-30,Test Supplier,100.00,21.00,150.00,draft,EUR"""

        wizard = self._create_wizard(csv_content)
        wizard.action_import_invoices()

        # Debe generar error porque 100 + 21 != 150
        self.assertEqual(wizard.created_count, 0)
        self.assertEqual(wizard.error_count, 1)

    def test_08_create_new_partner(self):
        """Test: crear proveedor nuevo si no existe."""
        csv_content = """move_type,name,invoice_date,partner_name,amount_untaxed,amount_tax,amount_total,state,currency_id
out_invoice,ST008,2025-12-30,New Supplier XYZ,100.00,21.00,121.00,draft,EUR"""

        # Verificar que no existe
        partner_before = self.env["res.partner"].search([
            ("name", "=", "New Supplier XYZ"),
        ])
        self.assertEqual(len(partner_before), 0)

        wizard = self._create_wizard(csv_content)
        wizard.action_import_invoices()

        # Debe haberse creado
        self.assertEqual(wizard.created_count, 1)

        partner_after = self.env["res.partner"].search([
            ("name", "=", "New Supplier XYZ"),
        ])
        self.assertEqual(len(partner_after), 1)
        self.assertEqual(partner_after.supplier_rank, 1)

    def test_09_multiple_commas_in_partner_name(self):
        """Test: partner con múltiples comas."""
        csv_content = """move_type,name,invoice_date,partner_name,amount_untaxed,amount_tax,amount_total,state,currency_id
out_invoice,ST009,2025-12-30,"Company Name, S.A., Sucursal Barcelona",100.00,21.00,121.00,draft,EUR"""

        wizard = self._create_wizard(csv_content)
        wizard.action_import_invoices()

        self.assertEqual(wizard.created_count, 1)

        invoice = self.env["account.move"].search([
            ("ref", "=", "ST009"),
            ("company_id", "=", self.company.id),
        ])

        self.assertEqual(invoice.partner_id.name, "Company Name, S.A., Sucursal Barcelona")

    def test_10_partner_with_comma_no_quotes_multiple_words(self):
        """Test: partner complejo sin comillas con coma en medio."""
        # Caso real problemático
        csv_content = """move_type,name,invoice_date,partner_name,amount_untaxed,amount_tax,amount_total,state,currency_id
out_invoice,ST010,2025-12-30,AUTOMOVILES Y TRACTORES, SOCIEDAD ANONIMA,500.00,105.00,605.00,draft,EUR"""

        wizard = self._create_wizard(csv_content)
        wizard.action_import_invoices()

        self.assertEqual(wizard.created_count, 1)
        self.assertEqual(wizard.error_count, 0)

        invoice = self.env["account.move"].search([
            ("ref", "=", "ST010"),
            ("company_id", "=", self.company.id),
        ])

        self.assertEqual(len(invoice), 1)
        # El nombre debe recomponerse correctamente
        self.assertEqual(
            invoice.partner_id.name,
            "AUTOMOVILES Y TRACTORES, SOCIEDAD ANONIMA"
        )

        # Verificar importes
        self.assertAlmostEqual(invoice.amount_untaxed, 500.00, places=2)
        self.assertAlmostEqual(invoice.amount_tax, 105.00, places=2)
        self.assertAlmostEqual(invoice.amount_total, 605.00, places=2)

