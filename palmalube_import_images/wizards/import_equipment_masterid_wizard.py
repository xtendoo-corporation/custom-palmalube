from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import xml.etree.ElementTree as ET

class ImportEquipmentMasterIdWizard(models.TransientModel):
    _name = 'import.equipment.masterid.wizard'
    _description = 'Importar y asignar ID externo a equipos'

    master_xml_file = fields.Binary(string='XML Maestro de Máquinas', required=True)
    master_xml_filename = fields.Char(string='Nombre XML Maestro')
    log = fields.Text(string='Log de Importación', readonly=True)

    def action_import_master_ids(self):
        self.ensure_one()
        log_lines = []
        master_map = self.parse_master_xml(self.master_xml_file)
        log_lines.append(f"Máquinas en XML maestro: {len(master_map)}")
        counters = {'Total procesadas': 0, 'Actualizadas': 0, 'No encontradas': 0, 'Duplicadas': 0}
        for ext_id, vals in master_map.items():
            counters['Total procesadas'] += 1
            domain = [('name', '=', vals['tipo_maquina'])]
            if vals['razon_social']:
                domain.append(('customer_id.name', '=', vals['razon_social']))
            if vals['numero_serie']:
                domain.append(('serial_no', '=', vals['numero_serie']))
            equipos = self.env['maintenance.equipment'].search(domain)
            if not equipos:
                counters['No encontradas'] += 1
                log_lines.append(f"[NO ENCONTRADA] {ext_id}: {vals}")
                continue
            if len(equipos) > 1:
                counters['Duplicadas'] += 1
                log_lines.append(f"[DUPLICADA] {ext_id}: {vals}")
                continue
            equipo = equipos[0]
            equipo.id_equipment = ext_id
            counters['Actualizadas'] += 1
            log_lines.append(f"[OK] {ext_id} asignado a equipo {equipo.display_name}")
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
        result = {}
        if not file_data:
            return result
        xml_bytes = base64.b64decode(file_data)
        root = ET.fromstring(xml_bytes)
        for rec in root.findall('.//DATA_RECORD'):
            ext_id = rec.findtext('ID_MAQUINA')
            tipo_maquina = rec.findtext('TIPO_MAQUINA') or ''
            razon_social = rec.findtext('RAZON_SOCIAL') or ''
            numero_serie = rec.findtext('NUMERO_SERIE') or ''
            if ext_id:
                result[str(ext_id)] = {
                    'tipo_maquina': tipo_maquina.strip(),
                    'razon_social': razon_social.strip(),
                    'numero_serie': numero_serie.strip(),
                }
        return result

