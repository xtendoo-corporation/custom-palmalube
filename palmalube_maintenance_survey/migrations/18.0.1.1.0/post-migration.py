# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Elimina la restricción SQL que impedía tener múltiples encuestas
    del mismo tipo en un mantenimiento.

    Ahora cada línea de equipo puede tener su propia encuesta independiente.
    """
    if not version:
        return

    _logger.info("Eliminando restricción 'maintenance_request_survey_unique' de survey_user_input")

    # Verificar si la restricción existe antes de intentar eliminarla
    cr.execute("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'survey_user_input'
        AND constraint_name = 'survey_user_input_maintenance_request_survey_unique'
    """)

    if cr.fetchone():
        cr.execute("""
            ALTER TABLE survey_user_input
            DROP CONSTRAINT IF EXISTS survey_user_input_maintenance_request_survey_unique
        """)
        _logger.info("Restricción 'maintenance_request_survey_unique' eliminada correctamente")
    else:
        _logger.info("La restricción ya no existe, no se requiere acción")

