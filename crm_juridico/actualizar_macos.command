#!/usr/bin/env bash
# ============================================================
#  Actualizador del CRM Juridico (macOS)
#  Descarga la ultima version y sobrescribe los archivos del
#  programa EN ESTA MISMA CARPETA.
#  Tu carpeta "data" (clientes, documentos, facturas) NO se toca.
# ============================================================
set -u
cd "$(dirname "$0")"

URL="https://github.com/gramguerr-prog/CILVIL-MERCANTIL/archive/refs/heads/claude/charming-hypatia-u2uMw.zip"
TMP="$(mktemp -d)"

fin() {
    rm -rf "$TMP"
}
trap fin EXIT

echo
echo "  Carpeta a actualizar: $(pwd)"
echo

if [ ! -f "main.py" ]; then
    echo "  ERROR: este archivo no esta en la carpeta del programa."
    echo "  Copialo dentro de la carpeta donde esta main.py y vuelve a ejecutarlo."
    read -r -p "  Pulsa Enter para cerrar..."
    exit 1
fi

echo "  [1/3] Descargando la ultima version..."
if ! curl -fsSL "$URL" -o "$TMP/crm.zip"; then
    echo "  ERROR: no se ha podido descargar. Revisa tu conexion a internet."
    read -r -p "  Pulsa Enter para cerrar..."
    exit 1
fi

echo "  [2/3] Extrayendo..."
mkdir -p "$TMP/extraido"
# Se extrae SOLO la carpeta del programa. El repositorio guarda ademas otros
# archivos cuyos nombres llevan acentos, y el unzip de macOS no siempre puede
# crearlos ("Illegal byte sequence"); ademas aqui no pintan nada.
# El </dev/null evita que unzip se quede esperando una respuesta si pregunta.
if ! unzip -q -o "$TMP/crm.zip" "*/crm_juridico/*" -d "$TMP/extraido" < /dev/null; then
    echo "  ERROR: no se ha podido extraer la actualizacion."
    read -r -p "  Pulsa Enter para cerrar..."
    exit 1
fi

SRC="$(find "$TMP/extraido" -maxdepth 2 -type d -name crm_juridico | head -1)"
if [ -z "$SRC" ] || [ ! -f "$SRC/main.py" ]; then
    echo "  ERROR: el archivo descargado no tiene el formato esperado."
    read -r -p "  Pulsa Enter para cerrar..."
    exit 1
fi

echo "  [3/3] Actualizando archivos del programa..."
DESTINO="$(pwd)"
YO="$(basename "$0")"
COPIA_OK=0

if command -v rsync >/dev/null 2>&1; then
    if rsync -a \
        --exclude 'data/' \
        --exclude '.venv/' \
        --exclude '__pycache__/' \
        --exclude "$YO" \
        "$SRC/" "$DESTINO/"; then
        COPIA_OK=1
    fi
else
    # Sin rsync: copia equivalente con tar, disponible en cualquier sistema.
    if (cd "$SRC" && tar cf - \
            --exclude='./data' \
            --exclude='./.venv' \
            --exclude='./__pycache__' \
            --exclude="./$YO" \
            .) | tar xf - -C "$DESTINO"; then
        COPIA_OK=1
    fi
fi

if [ "$COPIA_OK" -ne 1 ]; then
    echo
    echo "  ERROR: no se han podido copiar los archivos."
    echo "  Cierra el programa si lo tienes abierto y vuelve a intentarlo."
    read -r -p "  Pulsa Enter para cerrar..."
    exit 1
fi

chmod +x run_macos.command 2>/dev/null || true
chmod +x actualizar_macos.command 2>/dev/null || true

echo
echo "  ============================================"
echo "   ACTUALIZADO CORRECTAMENTE"
echo "   Tus datos siguen intactos en la carpeta data"
echo "  ============================================"
echo
echo "  Ya puedes cerrar esta ventana y abrir el programa"
echo "  con run_macos.command"
echo
read -r -p "  Pulsa Enter para cerrar..."
