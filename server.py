"""
Servidor MCP del Super Debugger.

Backend de depuracion basado en un tracer propio (sys.settrace, ver
debug_wrapper.py / debug_client.py) en vez de debugpy/DAP -- mas simple
y sin depender de un adapter externo.

Expone herramientas MCP para:
  - Inspeccionar y ejecutar scripts Python (read_file, run_script).
  - Depurar paso a paso con breakpoints (debug_run, debug_continue,
    debug_get_variables, debug_stop).
  - Modificar y revertir archivos (write_file, revert_file).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fastmcp import FastMCP

from debug_client import DebugClient

mcp = FastMCP("SuperDebugger")

# Sesiones de debug activas: path resuelto -> {"client": DebugClient, "last_event": dict}
_sessions: dict[str, dict] = {}

# Backups de archivos modificados: path resuelto -> contenido original
_backups: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Herramientas basicas
# ---------------------------------------------------------------------------

@mcp.tool()
def ping() -> str:
    """Verifica que el servidor responde."""
    return "pong - el servidor MCP esta funcionando"


# ---------------------------------------------------------------------------
# Herramientas de archivo
# ---------------------------------------------------------------------------

@mcp.tool()
def read_file(path: str) -> str:
    """Lee y devuelve el contenido completo de un archivo de texto, con
    numeros de linea al principio de cada linea (formato 'N: codigo') para
    poder referenciar lineas exactas al pedir breakpoints o escribir el fix.
    """
    p = Path(path).resolve()
    if not p.exists():
        return f"ERROR: el archivo {p} no existe."
    lines = p.read_text(encoding="utf-8").splitlines()
    return "\n".join(f"{i + 1}: {line}" for i, line in enumerate(lines))


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Sobreescribe un archivo con contenido nuevo completo (no un diff, el
    archivo entero). Guarda automaticamente el contenido original en memoria
    la primera vez que se toca ese archivo, para poder revertir.
    """
    p = Path(path).resolve()
    key = str(p)
    if key not in _backups:
        _backups[key] = p.read_text(encoding="utf-8") if p.exists() else ""
    p.write_text(content, encoding="utf-8")
    return f"Archivo {p.name} actualizado ({len(content)} caracteres)."


@mcp.tool()
def revert_file(path: str) -> str:
    """Restaura un archivo a como estaba antes del primer write_file de esta
    sesion. Usar si un intento de fix empeoro las cosas.
    """
    p = Path(path).resolve()
    key = str(p)
    if key not in _backups:
        return f"No hay backup guardado para {p.name} (nunca se modifico)."
    p.write_text(_backups[key], encoding="utf-8")
    return f"Archivo {p.name} revertido a su version original."


@mcp.tool()
def run_script(path: str, timeout: float = 10.0) -> str:
    """Corre un script Python normal (sin debugger) y devuelve su codigo de
    salida, stdout y stderr. Usar para comprobar si el script falla y,
    despues de aplicar un fix, para verificar si ya quedo corregido.
    """
    p = Path(path).resolve()
    if not p.exists():
        return f"ERROR: el archivo {p} no existe."
    try:
        result = subprocess.run(
            [sys.executable, str(p)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"TIMEOUT: el script no termino en {timeout}s (posible loop infinito)."

    status = "OK (exit 0)" if result.returncode == 0 else f"FALLO (exit {result.returncode})"
    return (
        f"{status}\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# Herramientas de debug
# ---------------------------------------------------------------------------

@mcp.tool()
def debug_run(file_path: str, breakpoints: list[int]) -> str:
    """Lanza el script bajo el tracer con los breakpoints dados y devuelve
    el primer STOP. Solo puede haber una sesion activa a la vez.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        return f"ERROR: el archivo {path} no existe."

    key = str(path)
    if key in _sessions:
        return f"ERROR: ya hay una sesion activa para {path}. Usa debug_stop primero."

    client = DebugClient()
    client.start(str(path), breakpoints)

    try:
        event = client.wait_for_stop(timeout=15.0)
    except TimeoutError as exc:
        client.stop()
        return f"ERROR: timeout esperando el primer breakpoint: {exc}"

    _sessions[key] = {"client": client, "last_event": event}
    return _format_event(event)


@mcp.tool()
def debug_continue(file_path: str) -> str:
    """Continua la ejecucion hasta el siguiente breakpoint o el fin del
    programa. Si el programa termina o falla, cierra la sesion automaticamente.
    """
    session = _get_session(file_path)
    if isinstance(session, str):
        return session

    client = session["client"]
    client.send_command("continue")
    try:
        event = client.wait_for_stop(timeout=15.0)
    except TimeoutError as exc:
        return f"ERROR: timeout esperando el siguiente evento: {exc}"

    session["last_event"] = event
    if event.get("event") in ("done", "error"):
        _sessions.pop(str(Path(file_path).resolve()), None)
        client.stop()
    return _format_event(event)


@mcp.tool()
def debug_get_variables(file_path: str) -> str:
    """Devuelve las variables locales del ultimo breakpoint alcanzado
    (no reanuda nada).
    """
    session = _get_session(file_path)
    if isinstance(session, str):
        return session

    event = session["last_event"]
    if event.get("event") != "stopped":
        return f"No hay variables disponibles (ultimo evento: {event.get('event')})."

    lines = [f"Variables en {event['function']} (linea {event['line']}):"]
    for name, value in event["locals"].items():
        if not name.startswith("__"):
            lines.append(f"  {name} = {value}")
    return "\n".join(lines)


@mcp.tool()
def debug_stop(file_path: str) -> str:
    """Termina la sesion de depuracion."""
    key = str(Path(file_path).resolve())
    session = _sessions.pop(key, None)
    if not session:
        return f"No hay sesion activa para {file_path}."
    session["client"].stop()
    return f"Sesion detenida: {Path(file_path).name}"


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _get_session(file_path: str):
    """Devuelve la sesion de debug activa para un path, o un mensaje de error."""
    key = str(Path(file_path).resolve())
    session = _sessions.get(key)
    if not session:
        return f"ERROR: no hay sesion activa para {file_path}. Usa debug_run primero."
    return session


def _format_event(event: dict) -> str:
    """Formatea un evento del tracer como texto legible para el LLM."""
    if event.get("event") == "stopped":
        vars_preview = ", ".join(
            f"{k}={v}" for k, v in event["locals"].items() if not k.startswith("__")
        )
        return (
            f"Detenido en {event['function']} (linea {event['line']}). "
            f"Variables: {vars_preview or '(ninguna)'}"
        )
    if event.get("event") == "error":
        return f"ERROR en el script depurado: {event['type']}: {event['message']}"
    if event.get("event") == "done":
        return "Programa terminado (sin mas breakpoints)."
    return f"Evento desconocido: {event}"


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")