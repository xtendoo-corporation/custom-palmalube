# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Maintenance Equipment Import Helper",
    "summary": "Facilita la importación de equipos de mantenimiento",
    "version": "18.0.1.0.0",
    "category": "Maintenance",
    "website": "https://github.com/xtendoo-corporation/custom-palmalube",
    "author": "Ivan Parrado, Manuel Calero, Xtendoo SLU",
    "license": "AGPL-3",
    "depends": [
        "maintenance",
        "maintenance_equipment_partner",
        "stock",
        "product",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_weight_volume_import_wizard.xml",
        # Aseguramos que el wizard se carga
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
