#!/usr/bin/env bash
# ============================================================
#  Arranque del CRM en macOS. Doble clic en este archivo.
#  La primera vez crea el entorno e instala las dependencias.
#  Si algo falla, la ventana NO se cierra: muestra el error.
# ============================================================
set -u
cd "$(dirname "$0")"

fallo() {
    echo
    echo "  ============================================"
    echo "   NO SE HA PODIDO ARRANCAR EL PROGRAMA"
    echo "  ============================================"
    echo
    echo "  $1"
    echo
    read -r -p "  Pulsa Enter para cerrar..."
    exit 1
}

if [ ! -f "main.py" ]; then
    fallo "Este archivo no está en la carpeta del programa (falta main.py)."
fi

if [ ! -x ".venv/bin/python" ]; then
    echo "  Primera ejecución: preparando el entorno. Puede tardar unos minutos."
    echo

    if ! command -v python3 >/dev/null 2>&1; then
        fallo "No se encuentra python3.
  Instálalo desde https://www.python.org/downloads/macos/
  y vuelve a abrir este archivo."
    fi

    if ! python3 -m venv .venv 2>/tmp/crm_venv_error.txt; then
        detalle="$(tail -3 /tmp/crm_venv_error.txt 2>/dev/null)"
        fallo "No se ha podido crear el entorno virtual.

  Lo más habitual es que falten las herramientas de desarrollo de Apple.
  Ejecuta en el Terminal:      xcode-select --install
  Acepta la instalación (tarda unos minutos) y vuelve a intentarlo.

  Detalle técnico:
  $detalle"
    fi

    # shellcheck disable=SC1091
    source .venv/bin/activate
    python -m pip install --upgrade pip >/dev/null 2>&1

    echo "  Instalando dependencias..."
    if ! python -m pip install -r requirements.txt; then
        fallo "No se han podido instalar las dependencias.
  Comprueba tu conexión a internet y vuelve a intentarlo."
    fi
    echo
else
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

python main.py || fallo "El programa se ha cerrado con un error.
  Revisa el mensaje que aparece encima de estas líneas."
