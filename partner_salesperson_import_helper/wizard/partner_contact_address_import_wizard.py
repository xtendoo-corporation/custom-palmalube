from odoo import models, fields, _
from odoo.exceptions import UserError
import base64
import io
import pandas as pd
import logging

_logger = logging.getLogger(__name__)

class PartnerContactAddressImportWizard(models.TransientModel):
    _name = 'partner.contact.address.import.wizard'
    _description = 'Importador de direcciones y contactos vinculados a clientes'

    file = fields.Binary('Archivo Excel', required=True)
    filename = fields.Char('Nombre del archivo')

    def action_import(self):
        _logger.info('INICIO IMPORTACIÓN DE DIRECCIONES Y CONTACTOS')
        if not self.file:
            _logger.error('No se subió archivo')
            raise UserError(_('Por favor, suba un archivo.'))
        try:
            data = base64.b64decode(self.file)
            df = pd.read_excel(io.BytesIO(data))
            df.columns = [c.strip().replace(' ', '_').replace('-', '_') for c in df.columns]
            _logger.info('Archivo leído correctamente. Columnas: %s', df.columns.tolist())
        except Exception as e:
            _logger.error('Error leyendo el archivo: %s', e)
            raise UserError(_('Error leyendo el archivo: %s') % e)
        col_id_cliente = 'ID_CLIENTE'
        col_persona_contacto = 'PERSONA_CONTACTO'
        col_tel_fijo = 'TELEFONO_FIJO'
        col_tel_movil = 'TELEFONO_MOVIL'
        col_dir = 'DIR_DESCRIPCION'
        col_prov = 'PROVI_DESCR'
        col_muni = 'MUNI_DESCR'
        col_cp = 'CODIGOPOSTAL'
        for col in [col_id_cliente, col_persona_contacto, col_tel_fijo, col_tel_movil, col_dir, col_prov, col_muni, col_cp]:
            if col not in df.columns:
                col_upper = col.upper()
                if col_upper in [c.upper() for c in df.columns]:
                    idx = [c.upper() for c in df.columns].index(col_upper)
                    df.rename(columns={df.columns[idx]: col}, inplace=True)
                else:
                    _logger.error('Falta columna: %s', col)
                    raise UserError(_('El archivo debe tener la columna: %s') % col)
        errores = []
        creados = 0
        for idx, row in df.iterrows():
            # Lógica robusta: buscar por ref exacta, por ref con punto de miles, y por ref sin punto de miles
            ref = str(row[col_id_cliente]).strip() if pd.notnull(row[col_id_cliente]) else None
            _logger.info('Fila %s: ref crudo: %r, tipo: %s', idx, row[col_id_cliente], type(row[col_id_cliente]))
            _logger.info('Fila %s: ref final usado para búsqueda: %r', idx, ref)
            partner = self.env['res.partner'].sudo().search([('ref', '=', ref)], limit=1)
            if not partner and ref:
                # Si la ref es numérica, probar con formato de miles (ej: 1737 -> 1.737)
                if ref.isdigit() and len(ref) > 3:
                    ref_miles = f"{int(ref):,}".replace(",", ".")
                    _logger.info('Fila %s: ref con punto de miles para búsqueda: %r', idx, ref_miles)
                    partner = self.env['res.partner'].sudo().search([('ref', '=', ref_miles)], limit=1)
                # Si la ref tiene punto de miles, probar quitando el punto
                if not partner and '.' in ref:
                    ref_no_puntos = ref.replace('.', '')
                    _logger.info('Fila %s: ref sin puntos para búsqueda: %r', idx, ref_no_puntos)
                    partner = self.env['res.partner'].sudo().search([('ref', '=', ref_no_puntos)], limit=1)
            if not partner:
                _logger.warning('No encontrado en Odoo: %s', ref)
                errores.append((ref, 'No encontrado en Odoo'))
                continue
            persona_contacto = str(row[col_persona_contacto]).strip() if pd.notnull(row[col_persona_contacto]) else ''
            tel_fijo = str(row[col_tel_fijo]).strip() if pd.notnull(row[col_tel_fijo]) else ''
            tel_movil = str(row[col_tel_movil]).strip() if pd.notnull(row[col_tel_movil]) else ''
            dir_descr = str(row[col_dir]).strip() if pd.notnull(row[col_dir]) else ''
            direccion = str(row['DIRECCION']).strip() if 'DIRECCION' in df.columns and pd.notnull(row['DIRECCION']) else ''
            prov_descr = str(row[col_prov]).strip() if pd.notnull(row[col_prov]) else ''
            muni_descr = str(row[col_muni]).strip() if pd.notnull(row[col_muni]) else ''
            # Leer código postal de la columna CODIGOPOSTAL (en mayúsculas)
            if 'CODIGOPOSTAL' in df.columns:
                _logger.info('Fila %s: Valor crudo CODIGOPOSTAL: %r', idx, row['CODIGOPOSTAL'])
                try:
                    cp = str(row['CODIGOPOSTAL']).strip() if pd.notnull(row['CODIGOPOSTAL']) else ''
                except Exception as e:
                    _logger.error('Fila %s: Error leyendo CODIGOPOSTAL: %s', idx, e)
                    cp = ''
            else:
                _logger.warning('Columna CODIGOPOSTAL no encontrada en el DataFrame')
                cp = ''
            _logger.info('Fila %s: Código postal a asignar (zip): %r', idx, cp)
            vals = {
                'parent_id': partner.id,
                'street': direccion,
                'zip': cp,  # Código postal correctamente añadido
                'city': muni_descr,
                'state_id': False,
                'phone': tel_fijo,
                'mobile': tel_movil,
                'country_id': self.env.ref('base.es').id if self.env.ref('base.es', raise_if_not_found=False) else False,
                'vat': '',  # NIF vacío SIEMPRE para contactos/direcciones creados
            }
            _logger.info('Fila %s: Diccionario vals para creación: %s', idx, vals)
            # Buscar provincia (state_id) por nombre
            country_id = vals['country_id']
            if prov_descr and country_id:
                state = self.env['res.country.state'].sudo().search([
                    ('name', 'ilike', prov_descr),
                    ('country_id', '=', country_id)
                ], limit=1)
                if state:
                    vals['state_id'] = state.id
            if persona_contacto:
                # Crear contacto vinculado al cliente
                vals['name'] = f"{persona_contacto} - {dir_descr}" if dir_descr else persona_contacto
                vals['type'] = 'contact'
            else:
                # Crear 'Otra dirección' vinculada al cliente
                vals['name'] = dir_descr
                vals['type'] = 'other'
            try:
                nuevo = self.env['res.partner'].sudo().create(vals)
                if nuevo.vat:
                    nuevo.sudo().write({'vat': ''})
                creados += 1
                _logger.info('Creado %s para ref %s: %s (parent: %s)', vals['type'], ref, vals['name'], partner.name)
            except Exception as e:
                _logger.error('Error creando %s para ref %s: %s (parent: %s)', vals.get('type'), ref, e, partner.name)
                errores.append((ref, str(e)))
        msg = _('Contactos/direcciones creados: %s') % creados
        if errores:
            msg += _('\nErrores: %s') % ', '.join([f"{c}: {e}" for c,e in errores])
        _logger.info('FIN IMPORTACIÓN. Total creados: %s. Errores: %s', creados, len(errores))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'partner.contact.address.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'name': _('Resultado de la importación'),
            'context': dict(self.env.context, default_filename=self.filename),
            'views': [(False, 'form')],
            'flags': {'form': {'action_buttons': False}},
            'message': msg,
        }
