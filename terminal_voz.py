#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
terminal_voz.py — Terminal de Linux controlada por voz.

Dictás comandos por voz, se ejecutan en una sesión de shell PERSISTENTE
(se mantienen cd, variables de entorno y demás entre comandos), se muestra
la salida y opcionalmente se lee en voz alta.

Seguridad: los comandos peligrosos piden confirmación explícita antes de
ejecutarse, porque el reconocimiento de voz se equivoca.

Uso básico:
    python3 terminal_voz.py

Controles por voz (palabras reservadas):
    "salir"        -> cierra la app
    "cancelar"     -> descarta lo dictado
    "repetir"      -> vuelve a leer la última salida
    "modo texto"   -> pasa a escribir el comando con el teclado

Tecla ENTER (sin hablar) = escribir el comando a mano (fallback).
"""

import os
import queue
import re
import sys
import threading

try:
    import pexpect
except ImportError:
    sys.exit("Falta 'pexpect'.  Instalá con:  pip install pexpect")

# pyttsx3 se importa ANTES que speech_recognition: su init carga el subsistema
# de audio (espeak/ALSA) lo que permite que PyAudio encuentre el dispositivo
# por defecto sin colgar al escanear la lista de PCMs.
try:
    import pyttsx3
    TTS_OK = True
except ImportError:
    TTS_OK = False

try:
    import speech_recognition as sr
except ImportError:
    sys.exit("Falta 'SpeechRecognition'.  Instalá con:  pip install SpeechRecognition")


# Prompt único para detectar cuándo termina cada comando en el shell.
PROMPT = "VOZ_TERM_9X7Q> "

# Elimina secuencias de escape ANSI/OSC y caracteres de control de la salida del shell.
# OSC va primero (termina en BEL o ST) para no confundirla con el ESC de un solo char.
_RE_ANSI = re.compile(
    r'\x1b\][^\x07]*\x07'          # OSC … BEL  (título de ventana, etc.)
    r'|\x1b\][^\x1b]*\x1b\\'       # OSC … ST
    r'|\x1b[@-Z\\-_]'              # Fe/Fs de un solo carácter
    r'|\x1b\[[0-?]*[ -/]*[@-~]'    # CSI (colores, cursor, etc.)
)
_RE_CTRL = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')  # preserva \t y \n


def _limpiar(texto: str) -> str:
    return _RE_CTRL.sub('', _RE_ANSI.sub('', texto))

# ---------------------------------------------------------------------------
# ALIAS DE VOZ  ->  COMANDO REAL
# Dictar sintaxis cruda es frustrante; mejor mapear frases naturales.
# Editá / agregá los tuyos libremente.
# ---------------------------------------------------------------------------
ALIAS = {
    "listar": "ls -la",
    "listar archivos": "ls -la",
    "donde estoy": "pwd",
    "subir un nivel": "cd ..",
    "ir a inicio": "cd ~",
    "limpiar": "clear",
    "fecha": "date",
    "quien soy": "whoami",
    "procesos": "ps aux",
    "espacio en disco": "df -h",
    "memoria": "free -h",
    "red": "ip a",
}

# ---------------------------------------------------------------------------
# PATRONES PELIGROSOS — pre-compilados para no recompilar en cada llamada.
# ---------------------------------------------------------------------------
_PATRONES_PELIGROSOS = [re.compile(p) for p in [
    r"\brm\s+(-[a-zA-Z]*r|--recursive)",    # rm recursivo, con o sin -f
    r"\bmkfs\b", r"\bdd\b", r"\bshred\b",
    r">\s*/dev/sd", r"\bof=/dev/",
    r":\(\)\s*\{",                          # fork bomb
    r"\bchmod\s+-R\b", r"\bchown\s+-R\b",
    r"\bshutdown\b", r"\breboot\b", r"\bhalt\b", r"\bpoweroff\b",
    r"\bfdisk\b", r"\bparted\b", r"\bmkswap\b",
    r"--no-preserve-root",
    r"\buserdel\b", r"\bgroupdel\b",
    r"\b(curl|wget)\b.*\|\s*(sudo\s+)?(ba)?sh",   # curl ... | sh
]]


def es_peligroso(comando: str) -> bool:
    return any(p.search(comando) for p in _PATRONES_PELIGROSOS)


class TerminalVoz:
    def __init__(self, idioma: str = "es-AR", leer_salida: bool = True):
        self.idioma = idioma
        self.leer_salida = leer_salida and TTS_OK
        self.ultima_salida = ""

        # --- Motor de voz (TTS) ---
        # Se inicializa en un hilo con timeout porque pyttsx3 puede colgar
        # si el driver de ALSA/espeak no responde.
        self.tts = None
        if self.leer_salida:
            _tts_ref = [None]
            def _init_tts():
                # Suprime el spam de ALSA/JACK que genera pyttsx3 al init.
                _fn = os.open(os.devnull, os.O_WRONLY)
                _fo = os.dup(2)
                os.dup2(_fn, 2)
                try:
                    eng = pyttsx3.init()
                    # El proxy de pyttsx3 arranca con _busy=True y no procesa
                    # la cola hasta runAndWait(). Para que rate/voice tengan
                    # efecto de inmediato, llamamos al driver directamente.
                    drv = eng.proxy._driver
                    drv.setProperty("rate", 175)
                    voices = eng.getProperty("voices")
                    es_voice = next(
                        (v.id for v in voices if "es-419" in v.id),
                        next((v.id for v in voices if v.id == "roa/es"), None)
                    )
                    if es_voice:
                        drv.setProperty("voice", es_voice)
                    _tts_ref[0] = eng
                except Exception:
                    pass
                finally:
                    os.dup2(_fo, 2)
                    os.close(_fn)
                    os.close(_fo)
            t = threading.Thread(target=_init_tts, daemon=True)
            t.start()
            t.join(timeout=5)
            self.tts = _tts_ref[0]
            if self.tts is None:
                self.leer_salida = False
            else:
                # Un único hilo toca el engine: pyttsx3 no es thread-safe y
                # dos runAndWait() en paralelo lo rompen en silencio.
                self._tts_cola = queue.Queue()
                threading.Thread(target=self._tts_worker, daemon=True).start()

        # --- Reconocedor de voz ---
        # Se silencia stderr durante la init de PyAudio/ALSA para evitar
        # los mensajes "Unknown PCM cards" del driver C que no son errores reales.
        self.rec = sr.Recognizer()
        _fd_null = os.open(os.devnull, os.O_WRONLY)
        _fd_old  = os.dup(2)
        os.dup2(_fd_null, 2)
        try:
            self.mic = sr.Microphone()
        except OSError as e:
            os.dup2(_fd_old, 2)
            sys.exit(f"No se encontró micrófono: {e}")
        finally:
            os.dup2(_fd_old, 2)
            os.close(_fd_null)
            os.close(_fd_old)

        print("Calibrando ruido ambiente (1 s)... quedate en silencio.")
        try:
            with self.mic as fuente:
                self.rec.adjust_for_ambient_noise(fuente, duration=1)
        except OSError as e:
            sys.exit(f"Error al acceder al micrófono: {e}")

        # --- Shell persistente ---
        try:
            self.shell = pexpect.spawn(
                "/bin/bash", encoding="utf-8", echo=False, timeout=30
            )
            # TERM=dumb y bracketed-paste off evitan secuencias de control en la salida.
            self.shell.sendline(
                f'export TERM=dumb PS1="{PROMPT}" PS2=""; '
                'bind "set enable-bracketed-paste off" 2>/dev/null; '
                'export NO_COLOR=1'
            )
            self.shell.expect_exact(PROMPT, timeout=10)
        except (pexpect.TIMEOUT, pexpect.EOF) as e:
            sys.exit(f"No se pudo inicializar el shell: {e}")

    def cerrar(self):
        """Cierra el shell subyacente liberando recursos."""
        try:
            self.shell.sendline("exit")
            self.shell.close(force=True)
        except Exception:
            pass

    # -------------------- Voz --------------------

    def _tts_worker(self):
        while True:
            texto, hecho = self._tts_cola.get()
            try:
                self.tts.say(texto)
                self.tts.runAndWait()
            except Exception:
                pass
            finally:
                hecho.set()

    def hablar(self, texto: str):
        if not (self.leer_salida and self.tts):
            return
        hecho = threading.Event()
        self._tts_cola.put((texto, hecho))
        hecho.wait(timeout=8)   # máx 8 s; si el driver de audio cuelga, se sigue sin voz

    def escuchar(self) -> str:
        """Retorna el texto reconocido, o '' si no entendió / hubo error."""
        try:
            with self.mic as fuente:
                print("\nEscuchando... (hablá ahora)")
                audio = self.rec.listen(fuente, timeout=8, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            print("(no escuché nada)")
            return ""
        except OSError as e:
            print(f"(error de micrófono: {e})")
            return ""

        try:
            texto = self.rec.recognize_google(audio, language=self.idioma)
            print(f"Entendí: «{texto}»")
            return texto.strip()
        except sr.UnknownValueError:
            print("(no entendí lo que dijiste)")
            return ""
        except sr.RequestError as e:
            print(f"(error del servicio de reconocimiento: {e})")
            return ""

    # -------------------- Traducción frase -> comando --------------------

    def a_comando(self, frase: str) -> str:
        f = frase.lower().strip()
        return ALIAS.get(f, frase.strip())

    # -------------------- Ejecución --------------------

    def ejecutar(self, comando: str):
        try:
            self.shell.sendline(comando)
            self.shell.expect_exact(PROMPT)
        except pexpect.TIMEOUT:
            print("El comando tardó demasiado (timeout).")
            return
        except pexpect.EOF:
            print("El shell se cerró inesperadamente.")
            sys.exit(1)

        salida = _limpiar(self.shell.before)
        lineas = salida.splitlines()
        # Con echo=False el shell no debería repetir el comando, pero algunos
        # init de bash sí lo hacen; se filtra si la primera línea coincide.
        if lineas and lineas[0].strip() == comando.strip():
            lineas = lineas[1:]
        salida = "\n".join(lineas).strip()

        self.ultima_salida = salida
        if salida:
            print("─" * 50)
            print(salida)
            print("─" * 50)
            self.hablar(" ".join(salida.splitlines()[:5]) or "Listo.")
        else:
            print("(sin salida)")
            self.hablar("Listo.")

    # -------------------- Bucle principal --------------------

    def loop(self):
        print("\n=== Terminal por voz lista ===")
        print("ENTER para escuchar  |  escribí un comando para mandarlo a mano")
        print("Decí 'salir' para terminar.\n")
        try:
            while True:
                try:
                    entrada = input("ENTER para hablar  >  ")
                except (EOFError, KeyboardInterrupt):
                    print("\nChau!")
                    break

                if entrada.strip():
                    if not self._procesar(entrada.strip()):
                        break
                    continue

                frase = self.escuchar()
                if not frase:
                    continue
                if not self._procesar(frase):
                    break
        finally:
            self.cerrar()

    def _procesar(self, frase: str) -> bool:
        """Procesa la frase. Retorna False cuando hay que salir del loop."""
        baja = frase.lower().strip(" .")

        if baja in ("salir", "cerrar", "terminar"):
            print("Cerrando. ¡Chau!")
            self.hablar("Cerrando.")
            return False

        if baja in ("cancelar", "cancela"):
            print("Cancelado.")
            return True

        if baja in ("repetir", "repetí", "repeti"):
            if self.ultima_salida:
                print(self.ultima_salida)
                self.hablar(" ".join(self.ultima_salida.splitlines()[:5]))
            return True

        if baja in ("modo texto", "teclado"):
            cmd = input("Escribí el comando: ").strip()
            if cmd:
                self._confirmar_y_ejecutar(cmd)
            return True

        self._confirmar_y_ejecutar(self.a_comando(frase))
        return True

    def _confirmar_y_ejecutar(self, comando: str):
        print(f"Comando: {comando}")
        if es_peligroso(comando):
            print("ADVERTENCIA: comando peligroso detectado.")
            self.hablar("Atención, comando peligroso. Confirmá.")
            resp = input("   Escribí 'si' para ejecutar: ").strip().lower()
            if resp not in ("si", "sí", "s", "yes", "y"):
                print("   Abortado.")
                return
        self.ejecutar(comando)


def main():
    app = TerminalVoz(idioma="es-AR", leer_salida=True)
    if not TTS_OK:
        print("(Nota: pyttsx3 no está instalado; no habrá lectura en voz alta.)")
    app.loop()


if __name__ == "__main__":
    main()
