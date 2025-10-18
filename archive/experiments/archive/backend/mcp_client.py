import os
import shlex
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class MCPServerSpec:
    """
    Descriptor for launching an MCP server via stdio.
    - command: executable (e.g., "npx")
    - args: arguments (e.g., ["-y", "@elevenlabs/elevenlabs-mcp"]) 
    - env_keys: environment variable names to forward if present
    """
    id: str
    command: str
    args: List[str]
    env_keys: List[str]


DEFAULT_SERVERS: Dict[str, MCPServerSpec] = {
    # ElevenLabs official MCP server (Python). Requires ELEVENLABS_API_KEY.
    # Repo: https://github.com/elevenlabs/elevenlabs-mcp
    # Start: Prefer `uvx elevenlabs-mcp` for isolated deps.
    "elevenlabs": MCPServerSpec(
        id="elevenlabs",
        command="uvx",
        args=["elevenlabs-mcp"],
        env_keys=["ELEVENLABS_API_KEY"],
    ),
    # Upstash Context7 MCP server (Node/NPX). Upstash env varies by setup.
    # Repo: https://github.com/upstash/context7
    # Common env: UPSTASH_VECTOR_REST_URL, UPSTASH_VECTOR_REST_TOKEN, UPSTASH_VECTOR_INDEX
    "context7": MCPServerSpec(
        id="context7",
        command="npx",
        args=["-y", "@upstash/context7-mcp@latest"],
        env_keys=[
            "UPSTASH_VECTOR_REST_URL",
            "UPSTASH_VECTOR_REST_TOKEN",
            "UPSTASH_VECTOR_INDEX",
        ],
    ),
}


def _collect_env(env_keys: List[str]) -> Dict[str, str]:
    env: Dict[str, str] = {}
    for k in env_keys:
        v = os.environ.get(k)
        if v is not None:
            env[k] = v
    return env


def _resolve_server_params(spec: MCPServerSpec):
    """
    Build StdioServerParameters with environment overrides:
    - MCP_<ID>_COMMAND: override command (default spec.command)
    - MCP_<ID>_ARGS:    override args as a shell string (default spec.args)
    """
    from mcp.client.stdio import StdioServerParameters  # type: ignore

    upper_id = spec.id.upper()
    cmd = os.environ.get(f"MCP_{upper_id}_COMMAND", spec.command)
    args_str = os.environ.get(f"MCP_{upper_id}_ARGS")
    args = shlex.split(args_str) if args_str else list(spec.args)

    env = os.environ.copy()
    env.update(_collect_env(spec.env_keys))

    return StdioServerParameters(command=cmd, args=args, env=env)


async def _open_session(spec: MCPServerSpec):
    """
    Open MCP client session to a given server spec.
    Returns an (session, aclose) tuple.

    Note: Requires the Python MCP client library.
    """
    try:
        # Import lazily so the backend can still start without MCP deps
        from mcp.client.session import ClientSession  # type: ignore
        from mcp.client.stdio import stdio_client  # type: ignore
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "Python MCP client is not installed. Add 'mcp' to backend/requirements.txt and pip install."
        ) from e

    # stdio_client in mcp>=1.x expects StdioServerParameters
    server_params = _resolve_server_params(spec)
    cm = stdio_client(server_params)
    ctx = await cm.__aenter__()
    read, write = ctx
    session = ClientSession(read, write)
    await session.__aenter__()
    # Initialize handshake per MCP spec (server may expose capabilities)
    await session.initialize()

    async def aclose():
        try:
            await session.__aexit__(None, None, None)
        finally:
            await cm.__aexit__(None, None, None)

    return session, aclose


async def list_tools(server_id: str) -> Dict[str, Any]:
    spec = DEFAULT_SERVERS.get(server_id)
    if not spec:
        raise ValueError(f"Unknown MCP server: {server_id}")

    session, aclose = await _open_session(spec)
    try:
        tools_result = await session.list_tools()
        tools = getattr(tools_result, "tools", tools_result)
        # Normalize minimal surface for the API response. Handle dicts, pydantic models, and objects.
        return {
            "server": server_id,
            "tools": [
                {
                    "name": (
                        t.get("name") if isinstance(t, dict)
                        else getattr(t, "name", None)
                        if not hasattr(t, "model_dump")
                        else t.model_dump().get("name")
                    ),
                    "description": (
                        t.get("description") if isinstance(t, dict)
                        else getattr(t, "description", None)
                        if not hasattr(t, "model_dump")
                        else t.model_dump().get("description")
                    ),
                    "inputSchema": (
                        t.get("inputSchema") if isinstance(t, dict)
                        else getattr(t, "inputSchema", None)
                        if not hasattr(t, "model_dump")
                        else t.model_dump().get("input_schema")
                    ),
                }
                for t in tools or []
            ],
        }
    finally:
        await aclose()


def _to_jsonable(obj: Any) -> Any:
    try:
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "dict"):
            return obj.dict()
        from dataclasses import is_dataclass, asdict  # type: ignore
        if is_dataclass(obj):
            return asdict(obj)
        return obj
    except Exception as e:  # noqa: BLE001
        return {"repr": repr(obj), "error": str(e)}


async def call_tool(server_id: str, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    spec = DEFAULT_SERVERS.get(server_id)
    if not spec:
        raise ValueError(f"Unknown MCP server: {server_id}")

    session, aclose = await _open_session(spec)
    try:
        result = await session.call_tool(tool_name, arguments or {})
        # Convert result to JSON-friendly form
        return {
            "server": server_id,
            "tool": tool_name,
            "result": _to_jsonable(result),
        }
    finally:
        await aclose()
