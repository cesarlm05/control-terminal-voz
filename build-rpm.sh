#!/usr/bin/env bash
# Compila el RPM de terminal-voz en Fedora.
set -euo pipefail

VERSION="1.0.0"
NAME="terminal-voz"

cd "$(dirname "$0")"

echo ">> Instalando herramientas de empaquetado (requiere sudo)..."
sudo dnf install -y rpm-build rpmdevtools

echo ">> Preparando el arbol de rpmbuild..."
rpmdev-setuptree

echo ">> Generando el tarball fuente desde los archivos actuales..."
tar czf "${NAME}-${VERSION}.tar.gz" \
    --transform "s,^,${NAME}-${VERSION}/," \
    LICENSE README.md requirements.txt terminal_voz.py

echo ">> Copiando fuentes y spec..."
cp "${NAME}-${VERSION}.tar.gz" ~/rpmbuild/SOURCES/
cp "${NAME}.spec"              ~/rpmbuild/SPECS/

echo ">> Construyendo el RPM..."
rpmbuild -ba ~/rpmbuild/SPECS/"${NAME}.spec"

echo
echo ">> Listo. El paquete quedo en:"
ls -1 ~/rpmbuild/RPMS/noarch/${NAME}-${VERSION}-*.noarch.rpm
echo
echo ">> Para instalarlo:"
echo "   sudo dnf install ~/rpmbuild/RPMS/noarch/${NAME}-${VERSION}-*.noarch.rpm"
