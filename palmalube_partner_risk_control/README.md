# Palmalube Partner Risk Control

## Descripción

Módulo para centralizar el control de riesgo comercial sobre clientes en Palmalube.

## Funcionalidades

Este módulo incluye:

1. **Control de riesgo en clientes**: Añade un booleano en `res.partner` para activar o desactivar el bloqueo por impago.
2. **Bloqueo en pedidos de venta**: Permite seleccionar el cliente en `sale.order`, pero lo limpia y muestra un aviso si está bloqueado. También refuerza el bloqueo en creación, edición y confirmación.
3. **Bloqueo en mantenimiento**: Permite seleccionar el cliente en `maintenance.request`, pero lo limpia y muestra un aviso si está bloqueado. También refuerza el bloqueo en creación y edición.
4. **Bloqueo en facturas de cliente**: Permite seleccionar el cliente en `account.move` para facturas de cliente, pero lo limpia y muestra un aviso si está bloqueado. También refuerza el bloqueo en creación, edición y publicación.
5. **Smart button de facturas pendientes**: Añade un botón inteligente en clientes para consultar sus facturas pendientes.

## Regla aplicada

Si el partner tiene activado el control y existen facturas de cliente publicadas, vencidas y pendientes de pago, no se permite:

- venderle en `sale.order`
- asignarlo en `maintenance.request`
- usarlo en facturas de cliente (`out_invoice`)

## Instalación

### Instalación en Odoo

1. Actualizar la lista de módulos
2. Buscar "Palmalube Partner Risk Control"
3. Instalar el módulo

## Autor

- Ivan Parrado
- Manuel Calero
- Abraham Carrasco

**Xtendoo SLU**

## Licencia

AGPL-3

