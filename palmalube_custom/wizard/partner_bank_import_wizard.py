# Copyright 2025 Ivan Parrado, Manuel Calero, Xtendoo SLU
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import io
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:
    _logger.warning("openpyxl library not found. Please install it with: pip install openpyxl")
    openpyxl = None


class PartnerBankImportWizard(models.TransientModel):
    _name = 'partner.bank.import.wizard'
    _description = 'Importar Cuentas Bancarias desde Excel'

    file = fields.Binary(
        string='Archivo Excel',
        required=True,
        help='Archivo Excel (.xlsx) con las columnas: ID_CLIENTE, RAZON_SOCIAL, IBAN'
    )
    filename = fields.Char(string='Nombre del archivo')

    # Campos de resultado
    total_lines = fields.Integer(string='Total de líneas procesadas', readonly=True)
    updated_count = fields.Integer(string='Cuentas actualizadas', readonly=True)
    created_count = fields.Integer(string='Cuentas creadas', readonly=True)
    skipped_count = fields.Integer(string='Líneas omitidas', readonly=True)
    error_count = fields.Integer(string='Errores', readonly=True)
    log_text = fields.Text(string='Log de importación', readonly=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Completado'),
    ], default='draft', string='Estado')

    def action_import(self):
        """Procesar el archivo Excel e importar las cuentas bancarias."""
        self.ensure_one()

        if not openpyxl:
            raise UserError(_(
                'La librería openpyxl no está instalada. '
                'Por favor, instálela ejecutando: pip install openpyxl'
            ))

        if not self.file:
            raise UserError(_('Por favor, seleccione un archivo Excel.'))

        # Decodificar el archivo
        try:
            file_data = base64.b64decode(self.file)
            workbook = openpyxl.load_workbook(io.BytesIO(file_data))
            sheet = workbook.active
        except Exception as e:
            raise UserError(_('Error al leer el archivo Excel: %s') % str(e))

        # Buscar las columnas relevantes
        header_row = None
        id_cliente_col = None
        razon_social_col = None
        iban_col = None

        # Buscar la fila de encabezados
        for row_idx, row in enumerate(sheet.iter_rows(max_row=10), start=1):
            for col_idx, cell in enumerate(row, start=1):
                if cell.value:
                    cell_value = str(cell.value).strip().upper()
                    if 'ID_CLIENTE' in cell_value:
                        id_cliente_col = col_idx
                        header_row = row_idx
                    elif 'RAZON_SOCIAL' in cell_value or 'RAZÓN_SOCIAL' in cell_value:
                        razon_social_col = col_idx
                    elif 'IBAN' in cell_value:
                        iban_col = col_idx

            if id_cliente_col and iban_col:
                break

        if not id_cliente_col or not iban_col:
            raise UserError(_(
                'No se encontraron las columnas requeridas en el Excel.\n'
                'Asegúrese de que el archivo contenga las columnas: ID_CLIENTE e IBAN'
            ))

        # Procesar las líneas
        log_lines = []
        total_lines = 0
        updated_count = 0
        created_count = 0
        skipped_count = 0
        error_count = 0

        ResPartner = self.env['res.partner']
        ResPartnerBank = self.env['res.partner.bank']

        for row_idx, row in enumerate(sheet.iter_rows(min_row=header_row + 1), start=header_row + 1):
            try:
                # Obtener valores de las celdas
                id_cliente = row[id_cliente_col - 1].value
                razon_social = row[razon_social_col - 1].value if razon_social_col else None
                iban = row[iban_col - 1].value

                # Validar datos mínimos
                if not id_cliente or not iban:
                    skipped_count += 1
                    continue

                # Limpiar y formatear datos
                id_cliente = str(id_cliente).strip()
                iban = str(iban).strip().replace(' ', '').upper()

                # Buscar el partner por ref
                partner = ResPartner.search([('ref', '=', id_cliente)], limit=1)

                if not partner:
                    log_lines.append(f"Línea {row_idx}: Cliente con ref '{id_cliente}' no encontrado")
                    error_count += 1
                    continue

                # Buscar si ya existe una cuenta bancaria con este IBAN para este partner
                existing_bank = ResPartnerBank.search([
                    ('partner_id', '=', partner.id),
                    ('acc_number', '=', iban)
                ], limit=1)

                if existing_bank:
                    log_lines.append(
                        f"Línea {row_idx}: IBAN {iban} ya existe para {partner.name} - Omitido"
                    )
                    skipped_count += 1
                    continue

                # Buscar si hay otras cuentas bancarias
                other_banks = ResPartnerBank.search([('partner_id', '=', partner.id)])

                # Crear la nueva cuenta bancaria
                ResPartnerBank.create({
                    'partner_id': partner.id,
                    'acc_number': iban,
                })

                created_count += 1
                log_lines.append(
                    f"Línea {row_idx}: ✓ Cuenta bancaria creada para {partner.name} (ref: {id_cliente})"
                )

                total_lines += 1

            except Exception as e:
                error_count += 1
                log_lines.append(f"Línea {row_idx}: ERROR - {str(e)}")
                _logger.error(f"Error procesando línea {row_idx}: {str(e)}")

        # Actualizar el wizard con los resultados
        self.write({
            'state': 'done',
            'total_lines': total_lines,
            'updated_count': updated_count,
            'created_count': created_count,
            'skipped_count': skipped_count,
            'error_count': error_count,
            'log_text': '\n'.join(log_lines),
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'partner.bank.import.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    def action_close(self):
        """Cerrar el wizard."""
        return {'type': 'ir.actions.act_window_close'}

