# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Proveedor",
        help="Proveedor del equipo de mantenimiento",
        tracking=True,
    )

    customer_id = fields.Many2one(
        comodel_name="res.partner",
        string="Cliente",
        help="Cliente asociado a este equipo de mantenimiento",
        tracking=True,
    )

    equipment_brand = fields.Char(
        string="Marca",
        help="Marca del equipo",
        tracking=True,
    )

    year_manufacture = fields.Integer(
        string="Año de Fabricación",
        help="Año de fabricación del equipo",
        tracking=True,
    )

    maintenance_price = fields.Float(
        string="Precio de Mantenimiento",
        help="Precio del mantenimiento del equipo",
        tracking=True,
        digits='Product Price',
    )

    note = fields.Html(
        string="Descripción",
        help="Descripción detallada del equipo",
        tracking=True,
    )
    image_1920 = fields.Image(
        string="Imagen",
        help="Imagen del equipo de mantenimiento",
        max_width=1920,
        max_height=1920,
    )
    images_ids = fields.One2many(
        comodel_name='maintenance.equipment.image',
        inverse_name='equipment_id',
        string='Imágenes adicionales',
    )
    id_equipment = fields.Char(
        string="ID Equipo",
        help="Identificador único del equipo",
    )
