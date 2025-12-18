# Palmalube Custom

## Descripción

Módulo de customizaciones para Palmalube que incluye:

1. **Cancelar pedidos de venta sin wizard**: Permite cancelar pedidos directamente sin mostrar el wizard de confirmación.
2. **Importar cuentas bancarias desde Excel**: Wizard para actualizar masivamente las cuentas bancarias de los clientes desde un archivo Excel.

## Importar Cuentas Bancarias

### Ubicación del menú

Contactos > Configuración > Importar Cuentas Bancarias

### Formato del archivo Excel

El archivo debe ser formato `.xlsx` (Excel) y contener las siguientes columnas:

- **ID_CLIENTE**: Referencia del cliente en Odoo (campo `ref` de `res.partner`)
- **RAZON_SOCIAL**: Nombre del cliente (informativo, se usa para validación)
- **IBAN**: Número de cuenta bancaria en formato IBAN

**Ejemplo:**

| ID_CLIENTE | RAZON_SOCIAL        | IBAN                       |
|------------|---------------------|----------------------------|
| CLI001     | Empresa Ejemplo SA  | ES9121000418450200051332   |
| CLI002     | Cliente Prueba SL   | ES7100302053091234567895   |

### Notas importantes

- Las columnas adicionales en el Excel serán ignoradas
- El sistema buscará el cliente por su referencia (`ref`)
- Si el cliente no existe, se mostrará un error en el log
- Si la cuenta bancaria ya existe para ese cliente, se omitirá
- Solo se procesarán líneas con `ID_CLIENTE` e `IBAN` válidos

### Proceso de importación

1. Ir a **Contactos > Configuración > Importar Cuentas Bancarias**
2. Seleccionar el archivo Excel
3. Hacer clic en **Importar**
4. Revisar el log de resultados que muestra:
   - Total de líneas procesadas
   - Cuentas creadas
   - Líneas omitidas
   - Errores encontrados
   - Log detallado línea por línea

## Instalación

### Requisitos

El módulo requiere la librería Python `openpyxl` para procesar archivos Excel:

```bash
pip install openpyxl
```

### Instalación en Odoo

1. Actualizar la lista de módulos
2. Buscar "Palmalube Custom"
3. Instalar el módulo

## Autor

- Ivan Parrado
- Manuel Calero
- Abraham Carrasco

**Xtendoo SLU**

## Licencia

AGPL-3

