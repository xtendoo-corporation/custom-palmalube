import base64
import tempfile
from odoo import models, fields, api


class ProductWeightVolumeImportWizard(models.TransientModel):
    _name = 'product.weight.volume.import.wizard'
    _description = 'Importar Peso y Volumen de Productos desde Excel'

    file = fields.Binary(string='Archivo Excel', required=True)
    filename = fields.Char(string='Nombre del archivo')

    def action_import(self):
        self.ensure_one()
        # Guardar archivo temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            tmp.write(base64.b64decode(self.file))
            tmp_path = tmp.name
        # Llamar al método de importación
        self.env['maintenance.equipment'].update_product_weight_volume_from_excel(tmp_path)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.weight.volume.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
            'context': dict(self.env.context, default_message='Importación completada.'),
        }

    def action_test_import(self):
        self.ensure_one()
        # Guardar archivo temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            tmp.write(base64.b64decode(self.file))
            tmp_path = tmp.name
        # Llamar al método de validación/prueba (puedes personalizar este método en el modelo destino)
        result = self.env['maintenance.equipment'].test_product_weight_volume_import(tmp_path)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.weight.volume.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'res_id': self.id,
            'context': dict(self.env.context, default_message=result or 'Prueba de importación completada.'),
        }
