# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    @api.model
    def _generate_unique_name(self):
        """Generar un nombre único para la solicitud de mantenimiento."""
        # Obtener el último número de solicitud
        last_request = self.search([], order='id desc', limit=1)
        if last_request:
            next_number = last_request.id + 1
        else:
            next_number = 1

        return f"Solicitud #{next_number}"

    @api.model
    def load(self, fields_list, data):
        """Sobrescribir load para generar automáticamente el campo name si está vacío."""

        # Si 'name' está en los campos pero viene vacío, generar uno automáticamente
        if 'name' in fields_list:
            name_index = fields_list.index('name')

            for row in data:
                # Si el campo name está vacío o es False
                if len(row) > name_index and (not row[name_index] or row[name_index] == ''):
                    # Generar un nombre único temporal (se regenerará en create)
                    row[name_index] = "AUTO_GENERATE"

        return super().load(fields_list, data)

    @api.model_create_multi
    def create(self, vals_list):
        """Generar automáticamente el campo name si no se proporciona."""
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'AUTO_GENERATE':
                # Generar nombre único usando secuencia
                vals['name'] = self.env['ir.sequence'].next_by_code('maintenance.request') or self._generate_unique_name()

        return super().create(vals_list)

