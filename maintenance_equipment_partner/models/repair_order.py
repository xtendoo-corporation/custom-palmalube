# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

class RepairOrder(models.Model):
    _inherit = 'repair.order'

    equipment_id = fields.Many2one('maintenance.equipment', string='Equipo')

