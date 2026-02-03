# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Palmalube Invoice report",
    "summary": "Customizaciones para Palmalube: factura personalizada",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "website": "https://github.com/xtendoo-corporation/custom-palmalube",
    "author": "Ivan Parrado, Manuel Calero, Abraham Carrasco Xtendoo SLU",
    "license": "AGPL-3",
    "depends": [
        "account",
        "l10n_es_sigaus_account",
        "l10n_es_sigaus_purchase",
        "l10n_es_sigaus_sale",
        "l10n_es_sigaus_stock_picking_report_valued",
    ],
    "data": [
        "views/invoice_report_inherit.xml",
    ],
    "installable": True,
    "application": False,
}
