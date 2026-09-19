"""
TravelPilot Tool Registry & Execution Engine
Provides registration, schema introspection, safe execution, and Gemini function declaration export.
"""

from dataclasses import dataclass
import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    func: Callable[..., Any]
    input_model: Optional[type[BaseModel]] = None


class ToolRegistry:
    """Manages and invokes agent tools deterministically."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters_schema: Dict[str, Any],
        func: Callable[..., Any],
        input_model: Optional[type[BaseModel]] = None,
    ) -> None:
        """Register a new tool with its schema and executor."""
        self._tools[name] = ToolDefinition(
            name=name,
            description=description.strip(),
            parameters_schema=parameters_schema,
            func=func,
            input_model=input_model,
        )
        logger.debug("Registered tool: %s", name)

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns metadata for all registered tools."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters_schema,
            }
            for t in self._tools.values()
        ]

    def execute(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Safely executes a tool by name with error containment.
        Returns:
            {
                "success": bool,
                "tool": tool_name,
                "result": Any (if success),
                "error": str (if failed)
            }
        """
        tool_def = self.get(tool_name)
        if not tool_def:
            return {
                "success": False,
                "tool": tool_name,
                "result": None,
                "error": f"Tool '{tool_name}' is not registered in the tool registry. Available tools: {list(self._tools.keys())}",
            }

        try:
            # Validate with input model if present
            if tool_def.input_model:
                validated_args = tool_def.input_model(**kwargs)
                res = tool_def.func(**validated_args.model_dump())
            else:
                res = tool_def.func(**kwargs)

            return {
                "success": True,
                "tool": tool_name,
                "result": res,
                "error": None,
            }
        except Exception as e:
            logger.exception("Error executing tool '%s': %s", tool_name, e)
            return {
                "success": False,
                "tool": tool_name,
                "result": None,
                "error": f"Execution failed: {str(e)}",
            }

    def to_gemini_declarations(self) -> List[Dict[str, Any]]:
        """Exports registered tools to Gemini FunctionDeclaration format."""
        declarations = []
        for t in self._tools.values():
            declarations.append(
                {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters_schema,
                }
            )
        return declarations


# Global registry instance
default_tool_registry = ToolRegistry()
