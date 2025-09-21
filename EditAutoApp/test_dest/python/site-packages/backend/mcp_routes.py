from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class MCPListRequest(BaseModel):
    server_id: str = Field(description="Server key: 'elevenlabs' or 'context7'")


class MCPCallRequest(BaseModel):
    server_id: str = Field(description="Server key: 'elevenlabs' or 'context7'")
    tool_name: str
    arguments: Optional[Dict[str, Any]] = None


@router.post("/api/mcp/tools")
async def mcp_list_tools(req: MCPListRequest):
    try:
        from . import mcp_client
        return await mcp_client.list_tools(req.server_id)
    except RuntimeError as e:
        # Likely missing MCP client library
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/mcp/call")
async def mcp_call_tool(req: MCPCallRequest):
    try:
        from . import mcp_client
        return await mcp_client.call_tool(req.server_id, req.tool_name, req.arguments)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(e))

