# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api

class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    repair_order_id = fields.Many2one("repair.order", "Orden de reparación")
    partner_id = fields.Many2one(
        "res.partner", string="Cliente",
        help="Cliente al que se le realiza el mantenimiento.")

    def action_create_repair_order(self):
        self.ensure_one()
        repair = self.env['repair.order'].create({
            'maintenance_request_ids': [(4, self.id)],
            'partner_id': self.partner_id.id if self.partner_id else False,
            'equipment_id': self.equipment_id.id if self.equipment_id else False,
            'name': self.name,
        })
        self.repair_order_id = repair.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'view_mode': 'form',
            'res_id': repair.id,
            'target': 'current',
        }

    def action_open_repair_order(self):
        self.ensure_one()
        if not self.repair_order_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'view_mode': 'form',
            'res_id': self.repair_order_id.id,
            'target': 'current',
        }
