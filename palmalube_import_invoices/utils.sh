.#!/bin/bash
# Comandos útiles para el módulo import_invoices_palmalube

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  COMANDOS ÚTILES - PALMALUBE_IMPORT_INVOICES              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo

# Variables
MODULE_PATH="/home/xtendoo/Documentos/odoo/18verifactu/odoo/custom/src/custom-palmalube/palmalube_import_invoices"
ODOO_PATH="/home/xtendoo/Documentos/odoo/18verifactu"

# Menú
PS3="Selecciona una opción: "
options=(
    "Ver estructura del módulo"
    "Verificar archivos"
    "Contar líneas de código"
    "Reiniciar Odoo (Docker)"
    "Ejecutar tests"
    "Ver CSV de prueba"
    "Ver documentación disponible"
    "Abrir wizard (info)"
    "Salir"
)

select opt in "${options[@]}"
do
    case $opt in
        "Ver estructura del módulo")
            echo "📁 Estructura del módulo:"
            cd "$MODULE_PATH"
            tree -L 2 2>/dev/null || find . -type d | sed -e 's;[^/]*/;|____;g;s;____|; |;g'
            echo
            ;;
        "Verificar archivos")
            echo "✅ Verificando archivos..."
            cd "$MODULE_PATH"
            echo
            echo "Archivos principales:"
            ls -lh __init__.py __manifest__.py LICENSE 2>/dev/null
            echo
            echo "Documentación:"
            ls -lh *.md 2>/dev/null
            echo
            echo "Código:"
            ls -lh wizards/*.py wizards/*.xml 2>/dev/null
            echo
            echo "Tests:"
            ls -lh tests/* 2>/dev/null
            echo
            ;;
        "Contar líneas de código")
            echo "📊 Estadísticas:"
            cd "$MODULE_PATH"
            echo "   Python: $(find . -name "*.py" | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}') líneas"
            echo "   XML: $(find . -name "*.xml" | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}') líneas"
            echo "   Tests: $(grep -c "def test_" tests/test_import_invoice_wizard.py 2>/dev/null || echo 0) tests"
            echo "   Documentación: $(cat *.md 2>/dev/null | wc -l) líneas"
            echo
            ;;
        "Reiniciar Odoo (Docker)")
            echo "🔄 Reiniciando Odoo..."
            cd "$ODOO_PATH"
            docker-compose restart odoo
            echo "✅ Odoo reiniciado"
            echo
            ;;
        "Ejecutar tests")
            echo "🧪 Ejecutando tests..."
            cd "$ODOO_PATH"
            docker-compose run --rm odoo odoo --test-enable --stop-after-init \
              --log-level=test -d devel -i palmalube_import_invoices
            echo
            ;;
        "Ver CSV de prueba")
            echo "📋 CSV de prueba:"
            cat "$MODULE_PATH/tests/test_invoices.csv"
            echo
            ;;
        "Ver documentación disponible")
            echo "📚 Documentación disponible:"
            cd "$MODULE_PATH"
            echo
            echo "1. README.md ($(stat -c%s README.md 2>/dev/null || stat -f%z README.md 2>/dev/null) bytes)"
            echo "   Documentación completa de usuario"
            echo
            echo "2. INSTALL.md ($(stat -c%s INSTALL.md 2>/dev/null || stat -f%z INSTALL.md 2>/dev/null) bytes)"
            echo "   Guía de instalación paso a paso"
            echo
            echo "3. ACCOUNTING_NOTES.md ($(stat -c%s ACCOUNTING_NOTES.md 2>/dev/null || stat -f%z ACCOUNTING_NOTES.md 2>/dev/null) bytes)"
            echo "   Notas técnicas contables"
            echo
            echo "4. QUICK_START.md ($(stat -c%s QUICK_START.md 2>/dev/null || stat -f%z QUICK_START.md 2>/dev/null) bytes)"
            echo "   Referencia rápida"
            echo
            echo "Para leer: cat $MODULE_PATH/<archivo>.md"
            echo
            ;;
        "Abrir wizard (info)")
            echo "🖥️  Para abrir el wizard en Odoo:"
            echo
            echo "   1. Acceder a Odoo (http://localhost:8069)"
            echo "   2. Ir a: Contabilidad → Proveedores"
            echo "   3. Clic en: Importación Palmalube"
            echo
            echo "O desde URL directa:"
            echo "   http://localhost:8069/web#action=palmalube_import_invoices.action_import_invoice_wizard"
            echo
            ;;
        "Salir")
            echo "👋 ¡Hasta luego!"
            break
            ;;
        *)
            echo "❌ Opción inválida"
            ;;
    esac
done

