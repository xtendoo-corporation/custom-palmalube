# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields
import logging
import re
try:
    import openpyxl
except ImportError:
    openpyxl = None

_logger = logging.getLogger(__name__)


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

    @api.model
    def update_product_weight_volume_from_excel(self, file_path):
        """
        Actualiza los campos weight y volume de los productos existentes según un archivo Excel.
        file_path: ruta absoluta al archivo Excel.
        """
        if not openpyxl:
            raise ImportError('Debe instalar openpyxl para usar esta función.')
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active
        headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
        # Normalizar nombres de columnas
        def norm(s):
            return s.strip().lower() if s else ''
        header_map = {norm(h): i for i, h in enumerate(headers)}
        def get_col(name):
            for k, v in header_map.items():
                if name.lower() in k:
                    return v
            return None
        idx_id = get_col('id_articulo')
        idx_qty = get_col('cantidad_unimed_envase')
        idx_env = get_col('envase')
        idx_sigaus = get_col('aporta_sigaus')
        if None in (idx_id, idx_qty, idx_env, idx_sigaus):
            raise ValueError('No se encontraron las columnas necesarias en el Excel.')
        # Recorrer filas
        total_filas = 0
        filas_procesadas = 0
        productos_modificados = set()
        for row in ws.iter_rows(min_row=2):
            fila_excel = row[0].row
            _logger.info(f'Procesando fila {fila_excel}')
            id_articulo = str(row[idx_id].value).strip() if row[idx_id].value else ''
            cantidad = row[idx_qty].value
            aporta_sigaus = row[idx_sigaus].value
            _logger.info(f'Fila {fila_excel}: id_articulo={id_articulo}, cantidad={cantidad}, aporta_sigaus={aporta_sigaus}')
            if aporta_sigaus != 1:
                _logger.info(f'Fila {fila_excel}: APORTA_SIGAUS distinto de 1, se omite.')
                continue
            if not id_articulo or not cantidad:
                _logger.info(f'Fila {fila_excel}: id_articulo o cantidad vacíos, se omite.')
                continue
            # Buscar producto por default_code quitando puntos
            product = False
            for prod in self.env['product.template'].search([]):
                if prod.default_code and prod.default_code.replace('.', '') == id_articulo:
                    product = prod
                    break
            _logger.info(f'Fila {fila_excel}: id_articulo leído (repr): {repr(id_articulo)}')
            if not product:
                _logger.warning(f'Fila {fila_excel}: Producto no encontrado para ID_ARTICULO: {id_articulo} (comparando sin puntos).')
                continue
            try:
                cantidad_float = float(str(cantidad).replace(',', '.'))
                nuevo_peso = cantidad_float * 0.9
                product.weight = nuevo_peso
                product.sigaus_subject = 'yes'  # Valor técnico correcto para selection
                productos_modificados.add(product.id)
                filas_procesadas += 1
                _logger.info(f'Fila {fila_excel}: Asignado weight={nuevo_peso} y sigaus_subject="Sí" a {product.name}')
            except Exception as e:
                _logger.warning(f'Fila {fila_excel}: No se pudo asignar weight/sigaus_subject a {product.name}: {e}')
        _logger.info(f'=== RESUMEN IMPORTACIÓN PESO/VOLUMEN ===')
        _logger.info(f'Filas totales leídas en Excel: {total_filas}')
        _logger.info(f'Filas procesadas (productos modificados): {filas_procesadas}')
        _logger.info(f'Productos únicos modificados: {len(productos_modificados)}')
        if productos_modificados:
            codigos = self.env['product.template'].browse(list(productos_modificados)).mapped('default_code')
            _logger.info(f'Codigos internos de productos modificados: {codigos}')
        _logger.info(f'========================================')
        return True

    @api.model
    def test_product_weight_volume_import(self, file_path):
        """
        Realiza una validación de prueba sobre el archivo Excel de importación de peso y volumen.
        No realiza cambios en la base de datos, solo verifica que los datos sean correctos y reporta posibles errores.
        """
        if not openpyxl:
            return 'Debe instalar openpyxl para usar esta función.'
        try:
            wb = openpyxl.load_workbook(file_path)
            ws = wb.active
            headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
            def norm(s):
                return s.strip().lower() if s else ''
            header_map = {norm(h): i for i, h in enumerate(headers)}
            def get_col(name):
                for k, v in header_map.items():
                    if name.lower() in k:
                        return v
                return None
            idx_id = get_col('id_articulo')
            idx_qty = get_col('cantidad_unimed_envase')
            idx_env = get_col('envase')
            if None in (idx_id, idx_qty, idx_env):
                return 'No se encontraron las columnas necesarias en el Excel.'
            errores = []
            for row in ws.iter_rows(min_row=2):
                id_articulo = str(row[idx_id].value).strip() if row[idx_id].value else ''
                cantidad = row[idx_qty].value
                envase = str(row[idx_env].value).strip().lower() if row[idx_env].value else ''
                if envase not in ['kg.', 'ml.', 'l.']:
                    continue
                if not id_articulo or not cantidad:
                    errores.append(f'Fila {row[0].row}: ID_ARTICULO o cantidad vacíos.')
                    continue
                product = self.env['product.template'].search([('default_code', '=', id_articulo)], limit=1)
                if not product:
                    # Buscar en product.product
                    product_variant = self.env['product.product'].search([('default_code', '=', id_articulo)], limit=1)
                    if product_variant:
                        product = product_variant.product_tmpl_id
                if not product:
                    errores.append(f'Fila {row[0].row}: Producto no encontrado para ID_ARTICULO: {id_articulo}')
                    continue
                # Validar cantidad numérica
                try:
                    float(cantidad)
                except Exception:
                    errores.append(f'Fila {row[0].row}: Cantidad no numérica para {id_articulo}')
            if errores:
                return 'Errores encontrados:\n' + '\n'.join(errores)
            return 'Prueba de importación exitosa. No se encontraron errores.'
        except Exception as e:
            return f'Error al procesar el archivo: {e}'
