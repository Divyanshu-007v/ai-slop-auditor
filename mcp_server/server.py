"""
MCP Evidence Server — Model Context Protocol-style tool server.

This module implements an in-process MCP-style server that provides evidence
retrieval tools to the AI-Slop & Misinformation Auditor agents.

=== MCP PROTOCOL OVERVIEW ===

The Model Context Protocol (MCP) defines a standard interface for tools that
LLM-based agents can discover, inspect, and invoke. Key concepts:

  - **Tool Registration**: Tools are registered with a name, description, and
    JSON Schema defining their input parameters.
  - **Tool Discovery**: Clients call `list_tools()` to discover available tools
    and their schemas.
  - **Tool Invocation**: Clients call `call_tool(name, arguments)` to execute
    a tool and receive structured results.

This implementation mirrors the MCP interface but runs in-process (no IPC).

=== UPGRADE PATH TO STANDALONE MCP SERVER ===

TODO: To convert this to a real standalone MCP server:

  1. Install FastMCP:  pip install fastmcp
  2. Replace MCPEvidenceServer with a FastMCP app:
       from fastmcp import FastMCP
       mcp = FastMCP("evidence-server")
  3. Convert each tool function to use the @mcp.tool() decorator
  4. Run as standalone:  fastmcp run mcp_server/server.py
  5. Connect from agents using an MCP client (stdio or SSE transport)
  6. The tool schemas, names, and handlers can be reused as-is.

See: https://github.com/jlowin/fastmcp for FastMCP documentation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MCP Tool Schema — mirrors the MCP tool specification
# ---------------------------------------------------------------------------

@dataclass
class MCPToolSchema:
    """
    Schema for a single MCP tool.

    Mirrors the MCP protocol's Tool object:
      - name: Unique tool identifier
      - description: Human-readable description of what the tool does
      - input_schema: JSON Schema dict defining the tool's input parameters
      - handler: Callable that executes the tool logic

    In a real MCP server, the handler would be invoked via IPC.
    Here it is called directly in-process.
    """
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Any]


# ---------------------------------------------------------------------------
# MCP Evidence Server
# ---------------------------------------------------------------------------

class MCPEvidenceServer:
    """
    In-process MCP-style evidence server.

    Provides tool registration, discovery, and invocation following
    the Model Context Protocol interface pattern.

    Usage:
        server = MCPEvidenceServer()
        tools = server.list_tools()          # Discover available tools
        result = server.call_tool(           # Invoke a tool
            "retrieve_local_evidence",
            {"query": "coffee diabetes", "claim_type": "medical"}
        )

    The server loads local evidence fixtures on initialization so it
    works fully offline. Optional live API tools are registered as
    stubs that return informative messages when API keys are absent.
    """

    def __init__(self, fixtures_path: str | None = None):
        """
        Initialize the MCP Evidence Server.

        Args:
            fixtures_path: Path to evidence_fixtures.json.
                           Defaults to data/trusted_sources/evidence_fixtures.json
                           relative to this module.
        """
        self._tools: dict[str, MCPToolSchema] = {}
        self._fixtures: dict[str, list[dict]] = {}
        self._credibility: dict[str, dict] = {}

        # Load local evidence fixtures
        self._load_fixtures(fixtures_path)
        self._load_credibility()

        # Register all tools
        self._register_default_tools()

        logger.info(
            "MCPEvidenceServer initialized with %d tools and %d fixture claims",
            len(self._tools),
            len(self._fixtures),
        )

    # -------------------------------------------------------------------
    # MCP Interface Methods
    # -------------------------------------------------------------------

    def register_tool(self, schema: MCPToolSchema) -> None:
        """
        Register a tool with the server.

        Mirrors MCP's tool registration. Each tool must have a unique name.
        In a standalone MCP server, this would add the tool to the server's
        tool registry accessible via the tools/list endpoint.

        Args:
            schema: The MCPToolSchema defining the tool.
        """
        if schema.name in self._tools:
            logger.warning("Overwriting existing tool: %s", schema.name)
        self._tools[schema.name] = schema
        logger.debug("Registered tool: %s", schema.name)

    def list_tools(self) -> list[dict[str, Any]]:
        """
        List all registered tools and their schemas.

        Mirrors MCP's tools/list endpoint. Returns a list of tool
        descriptors including name, description, and input schema.

        Returns:
            List of tool descriptor dicts.
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Invoke a registered tool by name.

        Mirrors MCP's tools/call endpoint. Dispatches to the tool's
        handler function with the provided arguments.

        Args:
            name: The unique name of the tool to invoke.
            arguments: Dictionary of input arguments matching the tool's schema.

        Returns:
            Tool execution result as a dictionary.

        Raises:
            ValueError: If the tool name is not registered.
        """
        if name not in self._tools:
            available = ", ".join(self._tools.keys())
            raise ValueError(
                f"Tool '{name}' not found. Available tools: {available}"
            )

        tool = self._tools[name]
        arguments = arguments or {}

        logger.info("Calling tool: %s with args: %s", name, list(arguments.keys()))

        try:
            result = tool.handler(**arguments)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error("Tool '%s' failed: %s", name, str(e))
            return {"status": "error", "error": str(e)}

    # -------------------------------------------------------------------
    # Data Loading
    # -------------------------------------------------------------------

    def _load_fixtures(self, fixtures_path: str | None) -> None:
        """Load evidence fixtures from JSON file."""
        if fixtures_path is None:
            base_dir = Path(__file__).parent.parent
            fixtures_path = str(base_dir / "data" / "trusted_sources" / "evidence_fixtures.json")

        path = Path(fixtures_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._fixtures = data.get("claims", {})
            logger.info("Loaded %d fixture claims from %s", len(self._fixtures), path)
        else:
            logger.warning("Evidence fixtures not found at %s", path)

    def _load_credibility(self) -> None:
        """Load source credibility scores from JSON file."""
        base_dir = Path(__file__).parent.parent
        cred_path = base_dir / "data" / "trusted_sources" / "source_credibility.json"

        if cred_path.exists():
            with open(cred_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._credibility = data.get("source_types", {})
            logger.info("Loaded %d credibility types", len(self._credibility))
        else:
            logger.warning("Source credibility file not found at %s", cred_path)

    # -------------------------------------------------------------------
    # Tool Registration
    # -------------------------------------------------------------------

    def _register_default_tools(self) -> None:
        """Register all default MCP tools."""
        from mcp_server.tools import (
            make_retrieve_local_evidence,
            make_search_news,
            make_search_factcheck,
            make_search_pubmed,
            make_fetch_url_text,
            make_rank_sources,
        )

        # 1. retrieve_local_evidence — always available (offline)
        self.register_tool(MCPToolSchema(
            name="retrieve_local_evidence",
            description="Search local trusted evidence fixtures for evidence matching a query and claim type.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "claim_type": {"type": "string", "description": "Type of claim: medical, financial, political, etc."},
                },
                "required": ["query"],
            },
            handler=make_retrieve_local_evidence(self._fixtures),
        ))

        # 2. search_news — stub / optional live
        self.register_tool(MCPToolSchema(
            name="search_news",
            description="Search recent news articles for evidence. Uses live API if NEWS_API_KEY is set, otherwise returns stub.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "date_range": {"type": "string", "description": "Optional date range filter"},
                },
                "required": ["query"],
            },
            handler=make_search_news(),
        ))

        # 3. search_factcheck — stub / optional live
        self.register_tool(MCPToolSchema(
            name="search_factcheck",
            description="Search fact-checking databases for claim verification.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Claim text to fact-check"},
                },
                "required": ["query"],
            },
            handler=make_search_factcheck(),
        ))

        # 4. search_pubmed — stub / optional live
        self.register_tool(MCPToolSchema(
            name="search_pubmed",
            description="Search PubMed for medical/scientific research evidence.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Medical/scientific search query"},
                },
                "required": ["query"],
            },
            handler=make_search_pubmed(),
        ))

        # 5. fetch_url_text — stub
        self.register_tool(MCPToolSchema(
            name="fetch_url_text",
            description="Fetch text content from a URL. Stub in MVP — returns informational message.",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                },
                "required": ["url"],
            },
            handler=make_fetch_url_text(),
        ))

        # 6. rank_sources — always available (offline)
        self.register_tool(MCPToolSchema(
            name="rank_sources",
            description="Rank a list of evidence items by credibility and relevance.",
            input_schema={
                "type": "object",
                "properties": {
                    "evidence_list": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "List of evidence dicts to rank",
                    },
                },
                "required": ["evidence_list"],
            },
            handler=make_rank_sources(self._credibility),
        ))

    # -------------------------------------------------------------------
    # Convenience Accessors
    # -------------------------------------------------------------------

    @property
    def fixtures(self) -> dict[str, list[dict]]:
        """Access the loaded evidence fixtures."""
        return self._fixtures

    @property
    def credibility(self) -> dict[str, dict]:
        """Access the loaded credibility scores."""
        return self._credibility
