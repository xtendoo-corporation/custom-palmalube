# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    equipment_count = fields.Integer(
        string="Nº de Equipos",
        compute="_compute_equipment_count",
    )

    equipment_ids = fields.One2many(
        comodel_name="maintenance.equipment",
        inverse_name="customer_id",
        string="Equipos",
    )

    @api.depends("equipment_ids")
    def _compute_equipment_count(self):
        for partner in self:
            partner.equipment_count = len(partner.equipment_ids)

    def action_view_equipments(self):
        """Acción para mostrar los equipos del cliente"""
        self.ensure_one()
        action = self.env.ref("maintenance.hr_equipment_action").read()[0]
        action["domain"] = [("customer_id", "=", self.id)]
        action["context"] = {
            "default_customer_id": self.id,
        }
        return action

