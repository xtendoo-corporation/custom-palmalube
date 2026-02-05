# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError


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
        return {
            'name': 'Equipos',
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.equipment',
            'view_mode': 'list,form',
            'domain': [('customer_id', '=', self.id)],
            'context': {
                'default_customer_id': self.id,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vat = vals.get("vat")
            if vat:
                existing = self.env["res.partner"].search([("vat", "=", vat)], limit=1)
                if existing:
                    raise ValidationError("No se puede crear el contacto porque el NIF ya existe.")
        return super(ResPartner, self).create(vals_list)
