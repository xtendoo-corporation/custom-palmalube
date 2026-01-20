# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_cancel(self):
        """Cancelar pedido de venta directamente sin wizard"""
        return self.write({"state": "cancel"})

