# Compilar el RPM en Fedora

Este entorno no puede generar el `.rpm` binario (no tiene `rpmbuild`), pero
acá tenés el paquete fuente listo. En tu Fedora, el `.rpm` sale con un comando.

## Opción rápida (script)

```bash
chmod +x build-rpm.sh
./build-rpm.sh
```

El `.rpm` queda en `~/rpmbuild/RPMS/noarch/`.

## Paso a paso (manual)

```bash
# 1. Herramientas de empaquetado
sudo dnf install -y rpm-build rpmdevtools

# 2. Crear el árbol de rpmbuild en tu HOME
rpmdev-setuptree

# 3. Copiar el tarball fuente y el spec a su lugar
cp terminal-voz-1.0.0.tar.gz ~/rpmbuild/SOURCES/
cp terminal-voz.spec        ~/rpmbuild/SPECS/

# 4. Construir
rpmbuild -ba ~/rpmbuild/SPECS/terminal-voz.spec
```

El paquete final queda en:

```
~/rpmbuild/RPMS/noarch/terminal-voz-1.0.0-1.*.noarch.rpm
```

## Instalar

```bash
sudo dnf install ~/rpmbuild/RPMS/noarch/terminal-voz-1.0.0-1.*.noarch.rpm
```

Después se ejecuta simplemente con:

```bash
terminal-voz
```

## Nota sobre dependencias

El RPM exige `python3`, `python3-pexpect`, `python3-pyaudio` y `espeak-ng`
(todas en los repos de Fedora). `SpeechRecognition` y `pyttsx3` están marcadas
como recomendadas; si tu repo no las trae, instalalas con:

```bash
pip install SpeechRecognition pyttsx3
```
