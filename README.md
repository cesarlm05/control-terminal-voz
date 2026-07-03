# Terminal de Linux por voz

App de Python que te deja **dictar comandos por voz** y ejecutarlos en una
sesión de shell real y persistente. Muestra la salida en pantalla y la lee
en voz alta. Pide confirmación antes de correr comandos peligrosos.

## 1. Instalar dependencias del sistema

El reconocimiento de micrófono necesita PortAudio, y la voz necesita espeak:

```bash
# Debian / Ubuntu / Mint
sudo apt update
sudo apt install -y python3-pip portaudio19-dev python3-pyaudio espeak

# Fedora
sudo dnf install -y python3-pip portaudio-devel espeak

# Arch / Manjaro
sudo pacman -S python-pip portaudio espeak-ng
```

## 2. Instalar las librerías de Python

```bash
pip install -r requirements.txt
```

Si `pip install PyAudio` falla, asegurate de haber instalado `portaudio19-dev`
(o el paquete equivalente de tu distro) antes.

## 3. Ejecutar

La forma más simple (crea un entorno virtual `.venv`, instala las dependencias
y lanza la app; necesario en Arch/Manjaro y otras distros con PEP 668):

```bash
./run.sh
```

O, si manejás el entorno vos mismo:

```bash
python3 terminal_voz.py
```

Apretá **ENTER** y hablá. O escribí un comando directo si preferís el teclado.

## Comandos por voz reservados

| Decís          | Hace                                       |
|----------------|--------------------------------------------|
| salir          | cierra la app                              |
| cancelar       | descarta lo que dictaste                   |
| repetir        | vuelve a leer la última salida             |
| modo texto     | escribís el comando con el teclado         |

## Atajos de voz (frase -> comando)

Dictar sintaxis cruda por voz es incómodo, así que hay un diccionario de
atajos en el archivo `terminal_voz.py` (variable `ALIAS`). Por ejemplo:

- "listar" -> `ls -la`
- "donde estoy" -> `pwd`
- "espacio en disco" -> `df -h`

Agregá los tuyos editando esa parte del archivo. Si no hay atajo, lo que
dictás se manda al shell tal cual.

## Sobre sudo y contraseñas

Por seguridad **nunca dictes contraseñas por voz**. Cuando un comando con
`sudo` pida la clave, escribila a mano en la terminal. Tené en cuenta que
el reconocimiento mezcla mal las palabras en inglés (ej: nombres de comandos),
por eso conviene usar los atajos de voz para lo que más repitas.

## Notas

- El reconocimiento por defecto usa el servicio de Google y **necesita
  internet**. Para una versión 100% offline se puede cambiar a Vosk o Whisper
  (decime y te lo adapto).
- Idioma por defecto: `es-AR`. Cambialo a `en-US` en `main()` si vas a dictar
  comandos en inglés.
