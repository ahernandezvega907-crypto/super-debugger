"""Wrapper que ejecuta un script bajo sys.settrace y emite JSON por stdout."""
import json
import os
import sys
import traceback


def _safe_repr(value) -> str:
    """repr() puede fallar con objetos que tienen __repr__ roto; no dejamos
    que eso tire abajo el trace function completo."""
    try:
        return repr(value)
    except Exception as exc:
        return f"<no representable: {type(exc).__name__}: {exc}>"


def run_with_breakpoints(script_path, breakpoint_lines):
    target_abs = os.path.abspath(script_path)
    target_norm = os.path.normcase(target_abs)
    breakpoints = set(breakpoint_lines)

    print(f"<<<INFO>>>Wrapper OK. Target={target_abs} BPs={sorted(breakpoints)}", flush=True)

    def trace(frame, event, arg):
        if event == 'line':
            filename_norm = os.path.normcase(os.path.abspath(frame.f_code.co_filename))
            if filename_norm == target_norm and frame.f_lineno in breakpoints:
                state = {
                    "event": "stopped",
                    "file": target_abs,
                    "line": frame.f_lineno,
                    "function": frame.f_code.co_name,
                    "locals": {k: _safe_repr(v) for k, v in frame.f_locals.items()},
                }
                print("<<<STOP>>>" + json.dumps(state), flush=True)
                cmd = sys.stdin.readline().strip()
                # Cadena vacia = stdin cerrado (EOF). Sin esto, un cierre
                # inesperado del pipe dejaria la sesion esperando para siempre.
                if cmd == "quit" or cmd == "":
                    sys.exit(0)
        return trace

    sys.settrace(trace)
    try:
        with open(script_path, encoding="utf-8") as f:
            source = f.read()
        code = compile(source, target_abs, 'exec')
        exec(code, {'__name__': '__main__', '__file__': target_abs})
    except SystemExit:
        pass
    except Exception as e:
        print("<<<ERROR>>>" + json.dumps({
            "event": "error",
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc(),
        }), flush=True)
    finally:
        sys.settrace(None)
    print("<<<DONE>>>", flush=True)


if __name__ == "__main__":
    script = sys.argv[1]
    lines = [int(x) for x in sys.argv[2:]]
    run_with_breakpoints(script, lines)
