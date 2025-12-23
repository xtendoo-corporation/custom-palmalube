{
    "name": "palmalube_import_images",
    "version": "18.0.1.0.0",
    "category": "Maintenance",
    "summary": "Importación masiva de imágenes de equipos de mantenimiento desde XML, Excel y ZIP.",
    "author": "Equipo Desarrollo Palmalube",
    "website": "https://palmalube.com",
    "license": "LGPL-3",
    "depends": ["maintenance"],
    "data": [
        "views/import_equipment_images_wizard.xml",
        "views/import_equipment_masterid_wizard.xml",
        "security/ir.model.access.csv"
    ],
    "application": False,
    "installable": True
}
