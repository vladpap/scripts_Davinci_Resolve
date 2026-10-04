# DaVinci Resolve Control Panel

Local web panel for running DaVinci Resolve Python scripts. The server binds to
`127.0.0.1` only and expects DaVinci Resolve to be running when its API is used.

## Run

```bash
cd resolve-panel
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

Open <http://127.0.0.1:8765/api/health> to inspect the connection status.

## Frontend development

```bash
cd resolve-panel/frontend
npm install
npm run dev
```

The Vite development server starts the dark React interface. During development,
requests beginning with `/api` are proxied to the backend at port `8765`.

## API contract

### `GET /api/health`

Checks the live DaVinci Resolve connection. A failed import, unavailable Resolve
instance, or stale Resolve connection returns a successful HTTP response with
`resolve_connected: false`; the next request retries the connection.

```json
{
  "resolve_connected": true,
  "version": "20.0.1.3"
}
```

When Resolve is unavailable, the response is:

```json
{
  "resolve_connected": false,
  "version": ""
}
```

### `GET /api/scripts`

Returns metadata for every valid Python file from `backend/scripts/`. Scripts are
discovered once at server startup; a restart is needed after adding or editing a
script. Files are parsed with `ast`, never imported or executed during discovery.

```json
[
  {
    "id": "add_markers",
    "name": "Add Markers to Timeline",
    "description": "Adds a marker at the start of every clip on the selected timeline track.",
    "params": [
      {
        "name": "color",
        "type": "select",
        "default": "Red",
        "options": ["Red", "Blue", "Green"]
      }
    ]
  }
]
```

### `GET /api/scripts/{id}`

Returns a single script manifest. Unknown identifiers return `404`.

### `POST /api/scripts/{id}/run`

Validates form values against the selected script manifest and queues it in a
dedicated worker thread. Resolve must be connected; otherwise the endpoint returns
`503`. Unknown values and invalid parameter types return `422`.

```json
{
  "params": {
    "track_type": "video",
    "track_index": 1,
    "color": "Blue",
    "note": "Review"
  }
}
```

Successful requests return `202 Accepted`:

```json
{
  "run_id": "dfacb6f5e3b7470bb9e401c7b4373a73",
  "status": "queued"
}
```

The current endpoint confirms that a run was accepted. Run completion, errors,
stopping, and live logs are provided by the WebSocket endpoint below.

### `POST /api/runs/{run_id}/stop`

Cancels a queued run and returns its final `cancelled` status. Python cannot
safely kill a synchronous function already executing in another thread, so a run
that has started returns `409 Conflict` and is allowed to finish normally.

### `WS /ws/logs/{run_id}`

Streams JSON events for one accepted run: its `queued`, `running`, and terminal
(`success`, `error`, or `cancelled`) status, standard output captured from the
script, exceptions, and the result preview. Events produced before the WebSocket
connects are replayed first.

## Script manifest

Each script is a `.py` file in `backend/scripts/` with a YAML document in its
module docstring. The filename becomes the API identifier and must use lowercase
letters, digits, and underscores. Supported parameter types are `text`, `number`,
`select`, `bool`, `textarea`, and `file`. A `select` parameter must declare a
non-empty `options` list and use one of those options as its default.

```python
"""
name: Example Script
description: A short description for the control panel.
params:
  - name: note
    type: text
    default: Hello
"""

def run(resolve, params):
    pass
```

## Project layout

```text
backend/
  main.py            # FastAPI application and endpoints
  resolve_bridge.py  # thin synchronous DaVinci Resolve API adapter
  script_loader.py   # manifest parsing and script registry
  runner.py          # validated background script execution
  scripts/           # user scripts and their YAML docstring manifests
frontend/
  src/components/ui/ # local shadcn/ui component foundation
  src/lib/           # shared frontend utilities
```
