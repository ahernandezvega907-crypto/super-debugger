"""Test del DebugClient con sys.settrace."""
from debug_client import DebugClient

print("=== 1. Iniciando wrapper ===")
client = DebugClient()
print(client.start("test_target.py", breakpoints=[7]))

print("\n=== 2. Esperando STOP ===")
try:
    event = client.wait_for_stop(timeout=15.0)
except TimeoutError as exc:
    print(f"TIMEOUT: {exc}")
    client.stop()
    raise SystemExit(1)

print(f"Evento: {event.get('event')}")
if event.get("event") == "stopped":
    print(f"  Archivo: {event['file']}")
    print(f"  Linea: {event['line']}")
    print(f"  Funcion: {event['function']}")
    print(f"  Variables:")
    for name, value in event["locals"].items():
        if not name.startswith("__"):
            print(f"    {name} = {value}")
elif event.get("event") == "error":
    print(f"  Tipo: {event['type']}")
    print(f"  Mensaje: {event['message']}")

print("\n=== 3. Enviando quit ===")
client.send_command("quit")
client.stop()
print("LISTO")