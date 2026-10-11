# 🐛 Super Debugger

**Servidor MCP para depurar código Python con IA — breakpoints, inspección de variables y ejecución paso a paso en tiempo real.**

[![MCP](https://img.shields.io/badge/MCP-compatible-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/python-3.12+-green)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/status-MVP-orange)]()

---

## 🤔 ¿Qué es Super Debugger?

Super Debugger es un **servidor MCP (Model Context Protocol)** que expone herramientas de depuración de Python a cualquier agente de IA compatible (Claude Desktop, Cursor, Cline, Continue, etc.).

En vez de que un LLM adivine la causa de un bug, Super Debugger le permite:

- **Ejecutar** el script y ver el traceback real
- **Detenerse** en breakpoints específicos
- **Inspeccionar** el valor de cada variable en vivo
- **Avanzar** la ejecución paso a paso
- **Modificar** el código y verificar el fix

Todo sin dependencias pesadas: no usa `debugpy`, ni DAP, ni `pdb`, ni PTYs. Solo `sys.settrace` de Python estándar.

---

## ✨ Características

| Herramienta MCP | Descripción |
| :--- | :--- |
| `ping` | Verifica que el servidor está vivo y responde |
| `read_file` | Lee archivos con números de línea (formato `N: código`) |
| `write_file` | Sobrescribe archivos con backup automático |
| `revert_file` | Restaura la versión original si un fix empeora las cosas |
| `run_script` | Ejecuta un script y devuelve exit code + stdout + stderr |
| `debug_run` | Lanza el script bajo el debugger con breakpoints |
| `debug_continue` | Avanza al siguiente breakpoint |
| `debug_get_variables` | Inspecciona variables del frame actual sin avanzar |
| `debug_stop` | Termina la sesión de debug |

**Valor único:** inspección de variables **en vivo** sin re-ejecutar ni adivinar.

---

## 📦 Instalación

### Requisitos

- Python 3.12 o superior
- [`uv`](https://github.com/astral-sh/uv) (recomendado) o `pip`

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/ahernandezvega907-crypto/super-debugger.git
cd super-debugger

# 2. Crear el entorno virtual
uv venv --python 3.12

# 3. Activar el entorno
# En Windows:
.venv\Scripts\activate
# En macOS/Linux:
source .venv/bin/activate

# 4. Instalar dependencias (desde pyproject.toml)
uv sync

# 5. Verificar que el servidor carga
python -c "from server import mcp; print('OK')"
```

---

## 🚀 Uso

### Opción 1: Claude Desktop

Edita `claude_desktop_config.json` (ubicación por sistema operativo):

| Sistema | Ruta |
| :--- | :--- |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

Agrega este bloque:

```json
{
  "mcpServers": {
    "super-debugger": {
      "command": "/ruta/absoluta/a/super-debugger/.venv/Scripts/python.exe",
      "args": ["/ruta/absoluta/a/super-debugger/server.py"]
    }
  }
}
```

⚠️ **Reemplaza la ruta** con la ubicación real donde clonaste el repo:
- **Windows:** `C:\\Users\\TuUsuario\\super-debugger\\.venv\\Scripts\\python.exe` y `C:\\Users\\TuUsuario\\super-debugger\\server.py`
- **macOS/Linux:** `/Users/TuUsuario/super-debugger/.venv/bin/python` y `/Users/TuUsuario/super-debugger/server.py`

**Importante:** apunta al `python` del `.venv` (no al global) para que el servidor encuentre `fastmcp`.

Reinicia Claude Desktop. Verás el ícono 🔌 en el chat.

### Opción 2: Cursor

Edita `~/.cursor/mcp.json` (o `%USERPROFILE%\.cursor\mcp.json` en Windows):

```json
{
  "mcpServers": {
    "super-debugger": {
      "command": "/ruta/absoluta/a/super-debugger/.venv/Scripts/python.exe",
      "args": ["/ruta/absoluta/a/super-debugger/server.py"]
    }
  }
}
```

⚠️ **Reemplaza la ruta** con la ubicación real donde clonaste el repo (mismas rutas que en Claude Desktop).

Reinicia Cursor y verás el servidor disponible en el chat.

### Opción 3: Cline (VS Code)

1. Instala la extensión **Cline** desde el Marketplace.
2. Abre el panel de Cline → **MCP Servers** → **Installed** → **Configure MCP Servers**.
3. Agrega este bloque en `cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "super-debugger": {
      "command": "C:\\Users\\TuUsuario\\super-debugger\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\TuUsuario\\super-debugger\\server.py"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Opción 4: Continue

1. Instala la extensión **Continue** desde el Marketplace.
2. Abre `~/.continue/config.yaml` (o `%USERPROFILE%\.continue\config.yaml` en Windows).
3. Agrega este bloque al final del archivo:

```yaml
mcpServers:
  - name: super-debugger
    command: "C:\\Users\\TuUsuario\\super-debugger\\.venv\\Scripts\\python.exe"
    args:
      - "C:\\Users\\TuUsuario\\super-debugger\\server.py"
    connectionTimeout: 120000
```

**Nota:** el `connectionTimeout: 120000` es obligatorio — FastMCP tarda más que el timeout por defecto en arrancar.

### Opción 5: MCP Inspector (para probar sin IDE)

```bash
npx -y @modelcontextprotocol/inspector python server.py
```

Abre `http://localhost:5173` en el navegador.

---

## ✅ Clientes validados

Ciclo completo de depuración (run → continue → inspeccionar variables → stop) probado end-to-end con:

| Cliente | Estado | Notas |
| :--- | :--- | :--- |
| MCP Inspector (oficial Anthropic) | ✅ Probado | Referencia protocol-level |
| Claude Desktop | ✅ Probado | Funciona out-of-the-box |
| VS Code + GitHub Copilot Chat | ✅ Probado | `mcp.json` debe apuntar al `.venv` |
| Cline | ✅ Probado | Requiere prompts explícitos con modelos gratuitos |
| Continue | ✅ Probado | Requiere `connectionTimeout: 120000` y prompts explícitos |
| Cursor | ⏳ No probado | Compatible con MCP, pendiente de verificar |

Ver [`VALIDATION.md`](VALIDATION.md) para los detalles técnicos, versiones de modelos y notas específicas de cada cliente.

**Nota sobre modelos gratuitos:** los modelos con soporte limitado de tool calling (ej. Gemini Flash Lite, Pixel Canary) requieren prompts explícitos del tipo:

> *"Usá EXCLUSIVAMENTE la herramienta MCP `debug_run` del servidor `super-debugger`, sin ejecutar comandos de terminal."*

Con esa instrucción, el tool calling funciona correctamente en todos los clientes probados.

---

## 🎬 Ejemplo de uso

**Código con bug (`test_target.py`):**

```python
def promedio_positivos(numeros):
    suma = 0
    cantidad = 0
    for i in range(len(numeros) + 1):  # ← bug: +1 de más
        if numeros[i] > 0:
            suma += numeros[i]
            cantidad += 1
    return suma / cantidad
```

**Lo que hace el agente:**

1. `run_script` → detecta `IndexError: list index out of range`
2. `read_file` → lee el código con números de línea
3. `debug_run` con breakpoint en línea 5 → se detiene y muestra `numeros=[4,-2,7,0,9], i=0`
4. `debug_continue` → avanza y ve cómo `i` llega hasta `5` (fuera de rango)
5. `write_file` → corrige: `range(len(numeros))` sin el `+1`
6. `run_script` → verifica: `OK (exit 0)` con el resultado correcto

**Sin adivinar. Sin re-ejecuciones infinitas. Solo inspección en vivo.**

---

## 🏗️ Arquitectura

```
Cliente MCP (Claude/Cursor/Cline/Continue)
        │ stdio (JSON-RPC)
        ▼
┌─────────────────────────┐
│  server.py (FastMCP)    │
│  9 herramientas         │
└───────────┬─────────────┘
            │ subprocess.PIPE
            ▼
┌─────────────────────────┐
│  debug_wrapper.py       │
│  sys.settrace           │
│  JSON por stdout        │
└─────────────────────────┘
```

**Decisiones de diseño:**

- **Sin debugpy:** la API DAP requiere un handshake de autenticación complejo que hace frágil la integración.
- **Sin pdb:** requiere TTY real, falla en subprocess.
- **Sin PTY:** los bugs de compatibilidad en Windows lo hacen poco fiable.
- **`sys.settrace`:** es la API oficial de Python, funciona igual en todos los sistemas.

---

## 🧪 Tests

```bash
# Test del backend de debug (offline, sin MCP)
python test_tools_offline.py

# Test del cliente debug
python test_debug.py
```

---

## 🛠️ Desarrollo

### Estructura del proyecto

```
super-debugger/
├── server.py              # Servidor MCP (herramientas expuestas)
├── debug_client.py        # Cliente del wrapper
├── debug_wrapper.py       # Motor de depuración (sys.settrace)
├── agent.py               # (opcional) Agente autónomo con LangGraph
│                          #   requiere ANTHROPIC_API_KEY (no incluido en el MVP)
├── test_*.py              # Tests
├── VALIDATION.md          # Evidencia de validación multi-cliente
├── pyproject.toml         # Dependencias
└── README.md              # Este archivo
```

### Dependencias

El proyecto usa **solo 3 dependencias runtime**:

- `fastmcp` — framework del servidor MCP
- `langgraph` — orquestación del agente autónomo (`agent.py`)
- `langchain-anthropic` — cliente de Claude para el agente

### Agregar nuevas herramientas

1. Define la función en `server.py` con el decorador `@mcp.tool()`.
2. Documenta el parámetro `Args:` en el docstring.
3. Reinicia el cliente MCP para recargar.

---

## 🗺️ Roadmap

- [x] MVP: 9 herramientas core
- [x] Compatibilidad con MCP Inspector
- [x] Validación end-to-end con 5 clientes (MCP Inspector, Claude Desktop, Copilot, Cline, Continue)
- [ ] Validación con Cursor
- [ ] Soporte para breakpoints condicionales
- [ ] Soporte para debugging multi-hilo
- [ ] Publicación en VS Code Marketplace
- [ ] Agente autónomo con modelo local (Ollama)

---

## 🤝 Contribuir

Pull requests son bienvenidas. Para cambios importantes, abrí un issue primero para discutir qué te gustaría cambiar.

---

## 📄 Licencia

MIT — usalo libremente en proyectos personales y comerciales.

---

## 🙏 Agradecimientos

- [FastMCP](https://github.com/jlowin/fastmcp) por el framework del servidor
- [Model Context Protocol](https://modelcontextprotocol.io) por el estándar
- Comunidad de Python por `sys.settrace`

---

**Hecho con 🐍 y ☕ por Armando Hernández**