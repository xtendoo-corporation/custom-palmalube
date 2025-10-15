# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Cliente",
        help="Cliente asociado a este equipo de mantenimiento",
        tracking=True,
    )

    equipment_model = fields.Char(
        string="Modelo",
        help="Modelo del equipo",
        tracking=True,
    )

    equipment_serial = fields.Char(
        string="Número de Serie",
        help="Número de serie del equipo",
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
