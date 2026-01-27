# palmalube_sale_type

Este módulo crea dos tipos de venta por defecto para Odoo 18:

- **Ventas**: Usa la secuencia estándar de ventas y el diario de ventas por defecto.
- **Reparacion**: Usa una secuencia personalizada que empieza por "REP/%(year)s/" y un diario de facturas propio "Facturas de reparaciones".

El diario de facturas se asigna automáticamente según el tipo de venta seleccionado en el pedido.
