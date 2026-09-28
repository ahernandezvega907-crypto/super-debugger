"""
Prueba las herramientas de agent.py SIN llamar a la API (no gasta credito).
Trabaja sobre una copia temporal de test_bug.py, no toca el original.
"""
import shutil
import tempfile
from pathlib import Path

import agent

SRC = Path(__file__).parent / "test_bug.py"
tmp_dir = Path(tempfile.mkdtemp())
target = str(tmp_dir / "bug_copia.py")
shutil.copy(SRC, target)


def paso(titulo):
    print(f"\n=== {titulo} ===")


paso("1. read_file (con numeros de linea)")
print(agent.read_file.invoke({"path": target}))

paso("2. run_script (debe FALLAR con IndexError)")
print(agent.run_script.invoke({"path": target}))

paso("3. debug_run con breakpoint en linea 5")
print(agent.debug_run.invoke({"file_path": target, "breakpoints": [5]}))

paso("4. debug_continue hasta que el script termine o falle")
for _ in range(10):
    out = agent.debug_continue.invoke({})
    print(out)
    if out.startswith(("ERROR", "Programa termino")):
        break

paso("5. debug_stop (no deberia haber sesion activa)")
print(agent.debug_stop.invoke({}))

paso("6. write_file con el fix (range sin el +1)")
fixed = Path(target).read_text(encoding="utf-8").replace(
    "range(len(numeros) + 1)", "range(len(numeros))"
)
print(agent.write_file.invoke({"path": target, "content": fixed}))

paso("7. run_script tras el fix (debe dar OK y 6.666...)")
print(agent.run_script.invoke({"path": target}))

paso("8. revert_file y confirmar que vuelve a fallar")
print(agent.revert_file.invoke({"path": target}))
print(agent.run_script.invoke({"path": target}))

shutil.rmtree(tmp_dir, ignore_errors=True)
print("\nPRUEBA OFFLINE TERMINADA")