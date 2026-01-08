# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Palmalube Import Invoices",
    "summary": "Importar facturas de proveedor desde CSV con validación contable exacta",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "website": "https://github.com/xtendoo-corporation",
    "author": "Xtendoo",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/import_invoice_wizard_views.xml",
    ],
}


