# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Palmalube Custom",
    "summary": "Customizaciones para Palmalube: cancelar pedidos sin wizard e importar cuentas bancarias",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "website": "https://github.com/xtendoo-corporation/custom-palmalube",
    "author": "Ivan Parrado, Manuel Calero, Abraham Carrasco Xtendoo SLU",
    "license": "AGPL-3",
    "depends": [
        "sale",
        "contacts",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/partner_bank_import_wizard_view.xml",
    ],
    "installable": True,
    "application": False,
}
