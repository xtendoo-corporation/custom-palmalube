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
        "stock",
        "repair",
        "maintenance_equipment_partner",
        "hr_maintenance",
        "maintenance_request_employee",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/account_payment_rules.xml",  # Añadida regla para comerciales
        "wizard/partner_bank_import_wizard_view.xml",
        "report/stock_picking_report.xml",
        "report/saleorder_albaran_report.xml",
        "report/saleorder_albaran_action.xml",
        "views/account_payment_views.xml",
        "views/sale_order_line_views.xml",
        "views/account_move_line_views.xml",
        "report/invoice_report_inherit.xml",
        "report/sale_report_inherit.xml",
        "actions/account_payment_update_comercial_from_chatter.xml",
        "views/maintenance_request_kanban_inherit.xml",
    ],
    "installable": True,
    "application": False,
}
