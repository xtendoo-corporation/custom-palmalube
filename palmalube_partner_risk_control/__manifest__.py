# Copyright 2026 Xtendoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Palmalube Partner Risk Control",
    "summary": "Controles de riesgo comercial para clientes",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "website": "https://github.com/xtendoo-corporation/custom-palmalube",
    "author": "Ivan Parrado, Manuel Calero, Abraham Carrasco Xtendoo SLU",
    "license": "AGPL-3",
    "depends": [
        "contacts",
        "account",
        "sale",
        "maintenance_request_repair",
        "maintenance_equipment_partner",
    ],
    "data": [
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
}

