# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    @api.model_create_multi
    def create(self, vals_list):
        """Crear equipos y validar fechas de solicitudes de mantenimiento."""
        # Crear los equipos
        equipments = super().create(vals_list)

        # Crear solicitudes de mantenimiento solo para fechas futuras
        from datetime import datetime
        today = datetime.now().date()

        for equipment in equipments:
            # Si el equipo tiene solicitudes importadas, verificar fechas
            for request in equipment.maintenance_ids:
                # Si la fecha programada es del pasado, eliminar la solicitud
                if request.schedule_date:
                    # Convertir datetime a date para comparar
                    schedule_date = request.schedule_date.date() if hasattr(request.schedule_date, 'date') else request.schedule_date
                    if schedule_date < today:
                        request.unlink()

        return equipments

    @api.model
    def load(self, fields, data):
        """Sobrescribir load para facilitar la importación de equipos."""

        # Manejar duplicados en serial_no añadiendo sufijo único
        if 'serial_no' in fields:
            serial_index = fields.index('serial_no')
            serials_in_import = []  # Rastrear números de serie en este archivo

            for row in data:
                if len(row) > serial_index and row[serial_index]:
                    serial_no = str(row[serial_index]).strip()

                    # Si el serial_no está vacío después de strip, saltarlo
                    if not serial_no:
                        continue

                    original_serial = serial_no

                    # Verificar si ya existe en la base de datos O en este archivo de importación
                    existing_in_db = self.search([('serial_no', '=', serial_no)], limit=1)

                    if existing_in_db or serial_no in serials_in_import:
                        # Añadir sufijo único para evitar duplicados
                        counter = 1
                        new_serial = f"{original_serial}-{counter}"

                        # Verificar tanto en BD como en el archivo actual
                        while (self.search([('serial_no', '=', new_serial)], limit=1) or
                               new_serial in serials_in_import):
                            counter += 1
                            new_serial = f"{original_serial}-{counter}"

                        serial_no = new_serial
                        row[serial_index] = serial_no

                    # Añadir a la lista de seriales en este archivo
                    serials_in_import.append(serial_no)

        # Limpiar formato de fecha en campos relacionados con maintenance_ids
        # (schedule_date, request_date, close_date)
        date_fields = ['maintenance_ids/schedule_date', 'maintenance_ids/request_date', 'maintenance_ids/close_date']

        for field_name in date_fields:
            if field_name in fields:
                date_index = fields.index(field_name)

                for row in data:
                    if len(row) > date_index and row[date_index]:
                        date_value = str(row[date_index]).strip()

                        # Eliminar milisegundos (.000) si existen
                        if '.' in date_value:
                            date_value = date_value.split('.')[0]

                        row[date_index] = date_value

        return super().load(fields, data)

