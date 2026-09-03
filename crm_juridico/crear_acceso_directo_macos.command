#!/usr/bin/env bash
# ============================================================
#  Crea "CRM Juridico.app" en el Escritorio del Mac.
#  Solo hay que ejecutarlo UNA VEZ. Despues puedes arrastrar
#  la app al Dock como cualquier otra.
# ============================================================
set -u
cd "$(dirname "$0")"
CARPETA="$(pwd)"

if [ ! -f "main.py" ]; then
    echo "  ERROR: esta carpeta no es la del programa (falta main.py)."
    read -r -p "  Pulsa Enter para cerrar..."
    exit 1
fi

APP="$HOME/Desktop/CRM Juridico.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>CRM Juridico</string>
    <key>CFBundleDisplayName</key>
    <string>CRM Jurídico</string>
    <key>CFBundleExecutable</key>
    <string>crm</string>
    <key>CFBundleIdentifier</key>
    <string>es.despacho.crmjuridico</string>
    <key>CFBundleIconFile</key>
    <string>crm.icns</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

cat > "$APP/Contents/MacOS/crm" <<LANZADOR
#!/bin/bash
cd "$CARPETA" || exit 1
if [ -x ".venv/bin/python" ]; then
    exec ./.venv/bin/python main.py
else
    # Primera vez: hay que preparar el entorno; se ve en el Terminal.
    exec open -a Terminal "$CARPETA/run_macos.command"
fi
LANZADOR
chmod +x "$APP/Contents/MacOS/crm"

if [ -f "recursos/crm.icns" ]; then
    cp "recursos/crm.icns" "$APP/Contents/Resources/crm.icns"
fi

# Refrescar el icono en el Finder
touch "$APP"

echo
echo "  ============================================"
echo "   APLICACION CREADA EN EL ESCRITORIO"
echo "  ============================================"
echo
echo "   $APP"
echo
echo "   Abrela con doble clic. Puedes arrastrarla al Dock."
echo "   La primera vez, macOS puede pedir confirmacion:"
echo "   pulsa con el boton derecho > Abrir."
echo
read -r -p "  Pulsa Enter para cerrar..."
