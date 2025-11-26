from odoo import models, fields, _
from odoo.exceptions import UserError
import base64
import io
import pandas as pd
import logging

_logger = logging.getLogger(__name__)

class PartnerSalespersonImportWizard(models.TransientModel):
    _name = 'partner.salesperson.import.wizard'
    _description = 'Importador de comerciales para clientes'

    file = fields.Binary('Archivo Excel', required=True)
    filename = fields.Char('Nombre del archivo')

    def action_import(self):
        if not self.file:
            raise UserError(_('Por favor, suba un archivo.'))
        try:
            data = base64.b64decode(self.file)
            df = pd.read_excel(io.BytesIO(data))
            df.columns = [c.lower() for c in df.columns]
        except Exception as e:
            raise UserError(_('Error leyendo el archivo: %s') % e)
        col_cliente = 'id_cliente'
        col_nombre = 'nombreagente'
        col_apellidos = 'apellidosagente'
        for col in [col_cliente, col_nombre, col_apellidos]:
            if col not in df.columns:
                raise UserError(_('El archivo debe tener la columna: %s') % col)
        updated = 0
        not_found = []
        not_updated = []
        for idx, row in df.iterrows():
            try:
                codigo_cliente = str(int(row[col_cliente])) if pd.notnull(row[col_cliente]) else None
                nombre_agente = str(row[col_nombre]).strip() if pd.notnull(row[col_nombre]) else ''
                apellidos_agente = str(row[col_apellidos]).strip() if pd.notnull(row[col_apellidos]) else ''
                nombre_completo = f"{nombre_agente} {apellidos_agente}".strip()
                nombre_completo_lower = nombre_completo.lower()
            except Exception:
                not_found.append((row.get(col_cliente), '', 'Datos no válidos'))
                continue
            if not codigo_cliente or not nombre_completo:
                not_found.append((row.get(col_cliente), '', 'Datos vacíos'))
                continue
            _logger.info(f"Buscando partner con ref={codigo_cliente}")
            partner = self.env['res.partner'].sudo().search([('ref', '=', codigo_cliente)], limit=1)
            if partner:
                _logger.info(f"Partner encontrado: ID={partner.id}, name={partner.name}, ref={partner.ref}, user_id antes={partner.user_id.id}, company_type={partner.company_type}")
            else:
                _logger.info(f"No se encontró partner con ref={codigo_cliente}")
            if not partner:
                not_found.append((codigo_cliente, '', 'Cliente no encontrado'))
                continue
            # Buscar usuario comercial por nombre completo normalizado o login generado
            login = f"auto_user_{nombre_completo_lower.replace(' ', '_')}@import.local"
            user = self.env['res.users'].sudo().search([('login', '=', login)], limit=1)
            if not user:
                # Buscar por nombre normalizado (ignorando mayúsculas, tildes y espacios)
                def normalize(s):
                    import unicodedata
                    return ''.join(c for c in unicodedata.normalize('NFKD', s.lower()) if not unicodedata.combining(c)).replace(' ', '')
                nombre_normalizado = normalize(nombre_completo)
                users = self.env['res.users'].sudo().search([])
                for u in users:
                    if u.name and normalize(u.name) == nombre_normalizado:
                        user = u
                        _logger.info(f"Usuario comercial ya existía por nombre normalizado: {user.id} ({user.name})")
                        break
            if not user:
                # Crear usuario con nombre completo y login único
                vals = {
                    'login': login,
                    'name': nombre_completo,
                }
                try:
                    user = self.env['res.users'].sudo().create(vals)
                    _logger.info(f"Usuario comercial creado: {user.id} ({user.name})")
                except Exception as e:
                    not_found.append((codigo_cliente, nombre_completo, f"No se pudo crear usuario: {e}"))
                    _logger.error(f"No se pudo crear usuario {nombre_completo}: {e}")
                    continue
            # No actualizar el nombre si el usuario ya existe, solo usarlo tal cual
            try:
                old_user = partner.user_id.id
                partner.sudo().write({'user_id': user.id})
                partner = self.env['res.partner'].sudo().browse(partner.id)
                _logger.info(f"user_id después={partner.user_id.id}")
                if partner.user_id.id == user.id:
                    updated += 1
                    _logger.info(f"Asignado user_id {user.id} a partner {partner.id}")
                else:
                    not_updated.append((codigo_cliente, nombre_completo, f"No se pudo actualizar (user_id previo: {old_user}, después: {partner.user_id.id})"))
                    _logger.warning(f"No se pudo actualizar user_id para partner {partner.id}")
            except Exception as e:
                not_updated.append((codigo_cliente, nombre_completo, f"Error: {e}"))
                _logger.error(f"Error actualizando partner {partner.id}: {e}")
        msg = _('Clientes actualizados: %s') % updated
        if not_found:
            msg += _('\nNo encontrados o inválidos: %s') % ', '.join([f"{c}/{u} ({r})" for c,u,r in not_found])
        if not_updated:
            msg += _('\nNo actualizados: %s') % ', '.join([f"{c}/{u} ({r})" for c,u,r in not_updated])
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'partner.salesperson.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'name': _('Resultado de la importación'),
            'context': dict(self.env.context, default_filename=self.filename),
            'views': [(False, 'form')],
            'flags': {'form': {'action_buttons': False}},
            'message': msg,
        }
