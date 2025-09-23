# MCP Setup (Context7 + ElevenLabs)

> **Note**: The primary TTS pipeline now uses Azure Speech Service exclusively. ElevenLabs MCP integration is considered legacy and is kept for archival purposes. The instructions below remain for teams still experimenting with ElevenLabs tooling.

This project includes an optional MCP proxy in the backend to let HTTP clients list tools and call tools from external MCP servers like Upstash Context7 and ElevenLabs.

Two ways to use MCP:

- Use from this backend (HTTP proxy): call `/api/mcp/tools` and `/api/mcp/call` to interact with MCP servers.
- Use directly from your MCP-capable client (e.g., Claude Desktop, Cursor): start the MCP servers with the scripts provided and configure your client to attach.

## 1) Prerequisites

- Node.js and npm installed (npx is required)
- Python backend dependencies installed

```bash
pip install -r backend/requirements.txt
```

## 2) Secrets and Environment

Do NOT commit secrets. Store locally via `.env` or environment exports.

- ElevenLabs: set `ELEVENLABS_API_KEY`
- Context7 (Upstash Vector): typically set
  - `UPSTASH_VECTOR_REST_URL`
  - `UPSTASH_VECTOR_REST_TOKEN`
  - `UPSTASH_VECTOR_INDEX`

Example `.env` entries (do not commit):

```
ELEVENLABS_API_KEY=...your_key_here...
UPSTASH_VECTOR_REST_URL=...optional...
UPSTASH_VECTOR_REST_TOKEN=...optional...
UPSTASH_VECTOR_INDEX=...optional...
```

## 3) Start MCP Servers (standalone)

Scripts are included to start each server via NPX:

```bash
# ElevenLabs MCP
source .env
bash scripts/start_mcp_elevenlabs.sh

# Context7 MCP
source .env
bash scripts/start_mcp_context7.sh
```

Refer to the repos for configuration and tool specifics:

- ElevenLabs MCP: https://github.com/elevenlabs/elevenlabs-mcp
- Context7 MCP: https://github.com/upstash/context7

## 4) Use MCP via Backend Proxy

The backend exposes minimal endpoints that launch the MCP server on-demand via stdio and proxy tool operations using the Python MCP client library.

Endpoints:

- `POST /api/mcp/tools` → list available tools
  - body: `{ "server_id": "elevenlabs" | "context7" }`

- `POST /api/mcp/call` → call a tool
  - body: `{ "server_id": "elevenlabs", "tool_name": "<tool>", "arguments": { ... } }`

Notes:

- The first time you call these, `npx` may fetch the MCP server package (requires network).
- The backend imports the Python MCP client lazily; if not installed, you will receive a 501 with guidance.

### Override server command/args via env

If the default npm package names are different from your environment, you can override the launch command without code changes:

- ElevenLabs
  - `MCP_ELEVENLABS_COMMAND=npx`
  - `MCP_ELEVENLABS_ARGS="-y <your-elevenlabs-mcp-package-or-github-spec>"`

- Context7
  - `MCP_CONTEXT7_COMMAND=npx`
  - `MCP_CONTEXT7_ARGS="-y <your-context7-mcp-package-or-github-spec>"`

Examples:

```
# ElevenLabs (Python server via uvx)
export MCP_ELEVENLABS_COMMAND=uvx
export MCP_ELEVENLABS_ARGS="elevenlabs-mcp"

# Context7 (Node server via npx)
export MCP_CONTEXT7_COMMAND=npx
export MCP_CONTEXT7_ARGS="-y @upstash/context7-mcp@latest"
```

The defaults in code already match these values, so env vars are only needed if you want to override.

## 5) MCP in Third-Party Clients

If you want to attach these servers directly in MCP-enabled tools (e.g., Claude Desktop), point the client to start commands:

- ElevenLabs: `npx -y @elevenlabs/elevenlabs-mcp`
- Context7: `npx -y @upstash/context7`

Make sure the environment contains the required variables (export or launch via a wrapper script that sources `.env`).
