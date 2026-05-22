#!/usr/bin/env bash
# Arranque del CRM en macOS. Doble click en este archivo.
# Crea el entorno virtual e instala dependencias la primera vez.
set -e
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
    echo "Creando entorno virtual..."
    if command -v python3 >/dev/null 2>&1; then
        python3 -m venv .venv
    else
        echo "No se encontró python3. Instálalo desde https://www.python.org/downloads/macos/"
        read -p "Pulsa enter para cerrar..."
        exit 1
    fi
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

python main.py
