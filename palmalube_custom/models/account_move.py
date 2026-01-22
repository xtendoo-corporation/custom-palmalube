# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    tiene_equipos_o_intervencion = fields.Boolean(
        string="¿Tiene equipos o intervención?",
        compute="_compute_tiene_equipos_o_intervencion",
        store=True,
    )

    def _compute_tiene_equipos_o_intervencion(self):
        for move in self:
            move.tiene_equipos_o_intervencion = any(
                bool(getattr(line, 'equipo_ids', False)) or bool(getattr(line, 'intervencion', False))
                for line in move.invoice_line_ids
            )
