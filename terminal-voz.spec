Name:           terminal-voz
Version:        1.0.0
Release:        1%{?dist}
Summary:        Terminal de Linux controlada por voz

License:        MIT
URL:            https://github.com/TU_USUARIO/terminal-voz
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel

# Dependencias disponibles en los repos de Fedora.
Requires:       python3
Requires:       python3-pexpect
Requires:       python3-pyaudio
Requires:       espeak-ng

# Estas vienen de PyPI y no siempre están empaquetadas en Fedora; si tu repo
# no las tiene, instalalas con:  pip install SpeechRecognition pyttsx3
Recommends:     python3-speechrecognition
Recommends:     python3-pyttsx3

%description
Aplicacion que permite dictar comandos por voz y ejecutarlos en una sesion de
shell persistente de Linux. Muestra la salida en pantalla, la lee en voz alta
y pide confirmacion explicita antes de ejecutar comandos peligrosos.

%prep
%setup -q

%build
# Nada que compilar: es un script de Python (noarch).

%install
rm -rf %{buildroot}
install -d -m 0755 %{buildroot}%{_bindir}
install -m 0755 terminal_voz.py %{buildroot}%{_bindir}/%{name}

%files
%license LICENSE
%doc README.md requirements.txt
%{_bindir}/%{name}

%changelog
* Thu Jun 11 2026 Tu Nombre <tu@correo.com> - 1.0.0-1
- Version inicial: terminal por voz con shell persistente, lectura en voz
  alta y confirmacion de comandos peligrosos.
