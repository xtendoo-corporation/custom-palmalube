# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
try:
    import openpyxl
except ImportError:
    openpyxl = None

class ImportEquipmentImagesWizard(models.TransientModel):
    _name = 'import.equipment.images.wizard'
    _description = 'Importar imágenes de equipos de mantenimiento'

    master_xml_file = fields.Binary(string='XML Maestro de Máquinas', required=True)
    master_xml_filename = fields.Char(string='Nombre XML Maestro')
    images_file = fields.Binary(string='Fichero de Imágenes (XML o Excel)', required=True)
    images_file_filename = fields.Char(string='Nombre Fichero de Imágenes')
    images_file_type = fields.Selection([
        ('xml', 'XML'),
        ('xlsx', 'Excel (.xlsx)')
    ], string='Tipo de Fichero de Imágenes', required=True)
    images_zip_file = fields.Binary(string='ZIP de Imágenes', required=True)
    images_zip_filename = fields.Char(string='Nombre ZIP de Imágenes')
    log = fields.Text(string='Log de Importación', readonly=True)

    def action_import_images(self):
        self.ensure_one()
        log_lines = []
        # 1. Parsear XML maestro
        master_map = self.parse_master_xml(self.master_xml_file)
        log_lines.append(f"Máquinas en XML maestro: {len(master_map)}")
        # 2. Parsear fichero de imágenes
        images_map = self.parse_images_file(self.images_file, self.images_file_type)
        log_lines.append(f"IDs de imágenes en fichero: {len(images_map)}")
        # 3. Cruzar ambos mapas
        matches = self.match_external_ids(master_map, images_map)
        log_lines.append(f"IDs cruzados: {len(matches)}")
        # 4. Procesar imágenes
        counters, details = self.process_zip_images(matches, master_map, images_map, self.images_zip_file)
        log_lines += details
        # 5. Resumen
        log_lines.append("\nResumen:")
        for k, v in counters.items():
            log_lines.append(f"{k}: {v}")
        self.log = '\n'.join(log_lines)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def parse_master_xml(self, file_data):
        """
        Devuelve: {ID_MAQUINA: {'tipo_maquina': ..., 'razon_social': ...}}
        """
        result = {}
        if not file_data:
            return result
        xml_bytes = base64.b64decode(file_data)
        root = ET.fromstring(xml_bytes)
        for rec in root.findall('.//DATA_RECORD'):
            ext_id = rec.findtext('ID_MAQUINA')
            tipo_maquina = rec.findtext('TIPO_MAQUINA') or ''
            razon_social = rec.findtext('RAZON_SOCIAL') or ''
            if ext_id:
                result[str(ext_id)] = {
                    'tipo_maquina': tipo_maquina.strip(),
                    'razon_social': razon_social.strip(),
                }
        return result

    def parse_images_file(self, file_data, file_type):
        """
        Devuelve: {ID_MAQUINA: [lista de nombres de archivo]}
        """
        result = {}
        if not file_data:
            return result
        if file_type == 'xml':
            xml_bytes = base64.b64decode(file_data)
            root = ET.fromstring(xml_bytes)
            for rec in root.findall('.//DATA_RECORD'):
                ext_id = rec.findtext('ID_MAQUINA')
                filename = rec.findtext('URL') or rec.findtext('NOMBRE')
                if ext_id and filename:
                    ext_id = str(ext_id)
                    if ext_id not in result:
                        result[ext_id] = []
                    result[ext_id].append(filename.strip())
        elif file_type == 'xlsx':
            if not openpyxl:
                raise UserError('openpyxl no está instalado en el entorno.')
            xlsx_bytes = base64.b64decode(file_data)
            wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), read_only=True)
            ws = wb.active
            for row in ws.iter_rows(min_row=2, values_only=True):
                ext_id, _, nombre, url, *_ = row
                filename = url or nombre
                if ext_id and filename:
                    ext_id = str(ext_id)
                    if ext_id not in result:
                        result[ext_id] = []
                    result[ext_id].append(str(filename).strip())
        return result

    def match_external_ids(self, master_map, images_map):
        """
        Devuelve: lista de IDs externos presentes en ambos mapas
        """
        return [ext_id for ext_id in master_map if ext_id in images_map and images_map[ext_id]]

    def find_equipment_in_odoo(self, ext_id):
        """
        Busca el equipo por id_equipment (que referencia al ID_MAQUINA externo).
        """
        return self.env['maintenance.equipment'].search([('id_equipment', '=', ext_id)])

    def process_zip_images(self, matches, master_map, images_map, zip_data):
        counters = {
            'Total procesadas': 0,
            'Importadas correctamente': 0,
            'Sin máquina en Odoo': 0,
            'Sin imagen en ZIP': 0,
            'Duplicadas en Odoo': 0,
        }
        details = []
        if not zip_data:
            details.append('ZIP de imágenes no proporcionado.')
            return counters, details
        zip_bytes = base64.b64decode(zip_data)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zip_files = {Path(f).name: f for f in zf.namelist()}
            for ext_id in matches:
                counters['Total procesadas'] += 1
                filenames = images_map[ext_id]
                equipments = self.find_equipment_in_odoo(ext_id)
                if not equipments:
                    counters['Sin máquina en Odoo'] += 1
                    details.append(f"[NO ENCONTRADA] {ext_id}")
                    continue
                if len(equipments) > 1:
                    counters['Duplicadas en Odoo'] += 1
                    details.append(f"[DUPLICADA EN ODOO] {ext_id} → {len(equipments)} equipos encontrados")
                    continue
                equipment = equipments[0]
                for idx, filename in enumerate(filenames):
                    if filename not in zip_files:
                        counters['Sin imagen en ZIP'] += 1
                        details.append(f"[SIN IMAGEN] {ext_id}: {filename}")
                        continue
                    image_data = zf.read(zip_files[filename])
                    if idx == 0:
                        equipment.image_1920 = base64.b64encode(image_data)
                        counters['Importadas correctamente'] += 1
                        details.append(f"[OK] {ext_id} → {filename} (principal)")
                    else:
                        self.env['maintenance.equipment.image'].create({
                            'equipment_id': equipment.id,
                            'image': base64.b64encode(image_data),
                            'name': filename,
                        })
                        counters['Importadas correctamente'] += 1
                        details.append(f"[OK] {ext_id} → {filename} (adicional)")
        return counters, details

