"""
Bloque C: agente autonomo de depuracion con LangGraph.

Flujo (decidido por el propio LLM via tool-calling, no hardcodeado a mano):
  1. Corre el script para ver si falla (run_script).
  2. Si falla, usa el debugger (debug_run/debug_continue/debug_get_variables)
     para inspeccionar variables en el punto del error antes de asumir nada.
  3. Escribe un fix (write_file) -- se guarda un backup del original la
     primera vez que se toca cada archivo, por si hay que revertir.
  4. Vuelve a correr (run_script) para verificar. Si sigue fallando, itera
     (hasta un limite de pasos) en vez de darse por vencido al primer intento.

Requiere:
    uv add langgraph langchain-anthropic
    variable de entorno ANTHROPIC_API_KEY seteada

Uso:
    python agent.py test_target.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent

from debug_client import DebugClient

# Backups de archivos tocados en esta corrida: path -> contenido original
_backups: dict[str, str] = {}

# Sesion de debug activa (una sola a la vez, alcanza para este agente)
_session: dict | None = None


# ---------- Herramientas de archivo ----------

@tool
def read_file(path: str) -> str:
    """Lee y devuelve el contenido completo de un archivo de texto, con
    numeros de linea al principio de cada linea (formato 'N: codigo') para
    poder referenciar lineas exactas al pedir breakpoints o escribir el fix."""
    p = Path(path).resolve()
    if not p.exists():
        return f"ERROR: el archivo {p} no existe."
    lines = p.read_text(encoding="utf-8").splitlines()
    return "\n".join(f"{i + 1}: {line}" for i, line in enumerate(lines))


@tool
def write_file(path: str, content: str) -> str:
    """Sobreescribe un archivo con contenido nuevo completo (no un diff,
    el archivo entero). Guarda automaticamente el contenido original en
    memoria la primera vez que se toca ese archivo, para poder revertir."""
    p = Path(path).resolve()
    key = str(p)
    if key not in _backups:
        _backups[key] = p.read_text(encoding="utf-8") if p.exists() else ""
    p.write_text(content, encoding="utf-8")
    return f"Archivo {p.name} actualizado ({len(content)} caracteres)."


@tool
def revert_file(path: str) -> str:
    """Restaura un archivo a como estaba antes del primer write_file de esta
    sesion. Usar si un intento de fix empeoro las cosas."""
    p = Path(path).resolve()
    key = str(p)
    if key not in _backups:
        return f"No hay backup guardado para {p.name} (nunca se modifico)."
    p.write_text(_backups[key], encoding="utf-8")
    return f"Archivo {p.name} revertido a su version original."


@tool
def run_script(path: str, timeout: float = 10.0) -> str:
    """Corre un script Python normal (sin debugger) y devuelve su codigo de
    salida, stdout y stderr. Usar para comprobar si el script falla y,
    despues de aplicar un fix, para verificar si ya quedo corregido."""
    p = Path(path).resolve()
    if not p.exists():
        return f"ERROR: el archivo {p} no existe."
    try:
        result = subprocess.run(
            [sys.executable, str(p)],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"TIMEOUT: el script no termino en {timeout}s (posible loop infinito)."

    status = "OK (exit 0)" if result.returncode == 0 else f"FALLO (exit {result.returncode})"
    return (f"{status}\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}")


# ---------- Herramientas de debug (envuelven debug_client.DebugClient) ----------

@tool
def debug_run(file_path: str, breakpoints: list[int]) -> str:
    """Lanza un script bajo el debugger con breakpoints en las lineas dadas
    y devuelve el primer STOP (linea, funcion y variables locales). Usar
    ANTES de debug_continue/debug_get_variables. Solo una sesion a la vez."""
    global _session
    if _session is not None:
        return "ERROR: ya hay una sesion de debug activa. Usa debug_stop primero."

    client = DebugClient()
    client.start(file_path, breakpoints)
    try:
        event = client.wait_for_stop(timeout=15.0)
    except TimeoutError as exc:
        client.stop()
        return f"ERROR: timeout esperando el primer breakpoint: {exc}"

    _session = {"client": client, "last_event": event}
    return _format_event(event)


@tool
def debug_continue() -> str:
    """Continua la ejecucion de la sesion de debug activa hasta el siguiente
    breakpoint o el fin del programa."""
    global _session
    if _session is None:
        return "ERROR: no hay sesion de debug activa. Usa debug_run primero."

    client = _session["client"]
    client.send_command("continue")
    try:
        event = client.wait_for_stop(timeout=15.0)
    except TimeoutError as exc:
        return f"ERROR: timeout esperando el siguiente evento: {exc}"

    _session["last_event"] = event
    if event.get("event") in ("done", "error"):
        client.stop()
        _session = None
    return _format_event(event)


@tool
def debug_get_variables() -> str:
    """Devuelve las variables locales del ultimo breakpoint alcanzado en la
    sesion de debug activa, sin reanudar la ejecucion."""
    if _session is None:
        return "ERROR: no hay sesion de debug activa."
    event = _session["last_event"]
    if event.get("event") != "stopped":
        return f"No hay variables disponibles (ultimo evento: {event.get('event')})."
    items = [f"{k} = {v}" for k, v in event["locals"].items() if not k.startswith("__")]
    return "Variables: " + (", ".join(items) if items else "(ninguna)")


@tool
def debug_stop() -> str:
    """Termina la sesion de debug activa, si hay alguna."""
    global _session
    if _session is None:
        return "No hay sesion de debug activa."
    _session["client"].stop()
    _session = None
    return "Sesion de debug detenida."


def _format_event(event: dict) -> str:
    if event.get("event") == "stopped":
        vars_preview = ", ".join(
            f"{k}={v}" for k, v in event["locals"].items() if not k.startswith("__")
        )
        return (f"Detenido en {event['function']} (linea {event['line']}). "
                f"Variables: {vars_preview or '(ninguna)'}")
    if event.get("event") == "error":
        return f"ERROR en el script depurado: {event['type']}: {event['message']}"
    if event.get("event") == "done":
        return "Programa termino sin mas breakpoints."
    return f"Evento desconocido: {event}"


# ---------- Agente ----------

SYSTEM_PROMPT = """Sos un agente de depuracion autonomo. Te dan la ruta de un
script Python que tiene un bug. Tu trabajo:

1. Corre el script con run_script para confirmar como falla (o si falla).
2. Lee el codigo fuente con read_file (te da numeros de linea).
3. Si la causa no es obvia solo con el traceback, usa debug_run con un
   breakpoint cerca de donde se rompe, y debug_continue/debug_get_variables
   para inspeccionar el estado real ANTES de asumir nada. No adivines
   valores de variables que podes simplemente inspeccionar.
4. Cuando tengas una causa raiz clara, escribi el archivo completo corregido
   con write_file (contenido completo, no un diff).
5. Volve a correr con run_script para verificar que ya funciona (exit 0).
6. Si sigue fallando, segui iterando: mas inspeccion, otro intento de fix.
   Si despues de varios intentos no lo lograste, usa revert_file para dejar
   el archivo como estaba y reporta honestamente que no pudiste arreglarlo
   y por que.
7. Terminá siempre la sesion de debug con debug_stop antes de responder,
   si dejaste una abierta.

Se especifico en tu respuesta final: que encontraste, que cambiaste y como
lo verificaste."""


def build_agent():
    model = ChatAnthropic(model="claude-sonnet-5", temperature=0)
    tools = [
        read_file, write_file, revert_file, run_script,
        debug_run, debug_continue, debug_get_variables, debug_stop,
    ]
    return create_react_agent(model=model, tools=tools, prompt=SYSTEM_PROMPT)


def main() -> None:
    if len(sys.argv) < 2:
        print("Uso: python agent.py <archivo_con_bug.py>")
        raise SystemExit(1)

    target = str(Path(sys.argv[1]).resolve())
    agent = build_agent()

    print(f"Agente arrancando sobre {target}...\n")
    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": f"Hay un bug en {target}. Diagnosticalo, arreglalo y verifica que quede corregido."}]},
            config={"recursion_limit": 50},
        )
    except GraphRecursionError:
        print("El agente alcanzo el limite de pasos sin confirmar un fix. Revisa el archivo manualmente.")
        if _session is not None:
            debug_stop.invoke({})
        raise SystemExit(1)

    final_message = result["messages"][-1]
    print("\n=== RESPUESTA FINAL DEL AGENTE ===")
    print(final_message.content)


if __name__ == "__main__":
    main()