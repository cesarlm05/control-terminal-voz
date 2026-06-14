#!/usr/bin/env bash
# Crea el entorno virtual si no existe, instala dependencias y lanza la app.
# Necesario en Arch/Manjaro (PEP 668) donde pip no puede instalar globalmente.

set -e
VENV=".venv"

if [ ! -d "$VENV" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv "$VENV"
fi

source "$VENV/bin/activate"

echo "Verificando dependencias..."
pip install -q -r requirements.txt

echo "Iniciando terminal por voz..."
python3 terminal_voz.py
