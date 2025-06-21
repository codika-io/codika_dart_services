"""
Dart Code Intelligence Service
Handles hover, completion, definitions, references, and symbol navigation
File: codika_dart_analyzer/dart_code_intelligence_service.py
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .dart_lsp_service import DartLSPService

logger = logging.getLogger(__name__)


class DartCodeIntelligenceService:
    """Service for code intelligence features like hover, completion, navigation"""

    def __init__(self, lsp_service: DartLSPService = None):
        self.lsp_service = lsp_service or DartLSPService()

    async def get_hover_info(self, file_path: str, line: int, character: int) -> Dict[str, Any]:
        """Get hover information at a specific position"""
        try:
            logger.info(f"Getting hover info for {file_path}:{line}:{character}")

            # Initialize session and open document
            if not await self.lsp_service.initialize_session():
                return {"success": False, "error": "Failed to initialize LSP session"}

            if not await self.lsp_service.open_document(file_path):
                return {"success": False, "error": f"Failed to open document: {file_path}"}

            # Send hover request
            params = {
                "textDocument": {"uri": self.lsp_service._file_to_uri(file_path)},
                "position": {"line": line - 1, "character": character - 1},
            }

            response = await self.lsp_service._send_request("textDocument/hover", params)

            # Close document
            await self.lsp_service.close_document(file_path)

            if response and "result" in response:
                result = response["result"]
                if result:
                    return {
                        "success": True,
                        "hover": self._process_hover_result(result),
                        "position": {"line": line, "character": character},
                    }
                else:
                    return {
                        "success": True,
                        "hover": None,
                        "message": "No hover information available at this position",
                    }
            else:
                return {"success": False, "error": "No response from language server"}

        except Exception as e:
            logger.error(f"Error getting hover info: {e}")
            return {"success": False, "error": str(e)}

    async def get_completion(
        self,
        file_path: str,
        line: int,
        character: int,
        trigger_character: str = None,
    ) -> Dict[str, Any]:
        """Get code completion suggestions at a position"""
        try:
            logger.info(f"Getting completion for {file_path}:{line}:{character}")

            if not await self.lsp_service.initialize_session():
                return {"success": False, "error": "Failed to initialize LSP session"}

            if not await self.lsp_service.open_document(file_path):
                return {"success": False, "error": f"Failed to open document: {file_path}"}

            params = {
                "textDocument": {"uri": self.lsp_service._file_to_uri(file_path)},
                "position": {"line": line - 1, "character": character - 1},
            }

            if trigger_character:
                params["context"] = {
                    "triggerKind": 2,  # TriggerCharacter
                    "triggerCharacter": trigger_character,
                }

            response = await self.lsp_service._send_request("textDocument/completion", params)
            await self.lsp_service.close_document(file_path)

            if response and "result" in response:
                result = response["result"]
                return {
                    "success": True,
                    "completions": self._process_completion_result(result),
                    "position": {"line": line, "character": character},
                }
            else:
                return {"success": False, "error": "No completion response"}

        except Exception as e:
            logger.error(f"Error getting completion: {e}")
            return {"success": False, "error": str(e)}

    async def get_definition(self, file_path: str, line: int, character: int) -> Dict[str, Any]:
        """Get definition location for symbol at position"""
        try:
            logger.info(f"Getting definition for {file_path}:{line}:{character}")

            if not await self.lsp_service.initialize_session():
                return {"success": False, "error": "Failed to initialize LSP session"}

            if not await self.lsp_service.open_document(file_path):
                return {"success": False, "error": f"Failed to open document: {file_path}"}

            params = {
                "textDocument": {"uri": self.lsp_service._file_to_uri(file_path)},
                "position": {"line": line - 1, "character": character - 1},
            }

            response = await self.lsp_service._send_request("textDocument/definition", params)
            await self.lsp_service.close_document(file_path)

            if response and "result" in response:
                result = response["result"]
                return {
                    "success": True,
                    "definitions": self._process_location_result(result),
                    "position": {"line": line, "character": character},
                }
            else:
                return {"success": False, "error": "No definition response"}

        except Exception as e:
            logger.error(f"Error getting definition: {e}")
            return {"success": False, "error": str(e)}

    async def get_references(
        self,
        file_path: str,
        line: int,
        character: int,
        include_declaration: bool = True,
    ) -> Dict[str, Any]:
        """Find all references to symbol at position"""
        try:
            logger.info(f"Getting references for {file_path}:{line}:{character}")

            if not await self.lsp_service.initialize_session():
                return {"success": False, "error": "Failed to initialize LSP session"}

            if not await self.lsp_service.open_document(file_path):
                return {"success": False, "error": f"Failed to open document: {file_path}"}

            params = {
                "textDocument": {"uri": self.lsp_service._file_to_uri(file_path)},
                "position": {"line": line - 1, "character": character - 1},
                "context": {"includeDeclaration": include_declaration},
            }

            response = await self.lsp_service._send_request("textDocument/references", params)
            await self.lsp_service.close_document(file_path)

            if response and "result" in response:
                result = response["result"]
                return {
                    "success": True,
                    "references": self._process_location_result(result),
                    "position": {"line": line, "character": character},
                    "total_references": len(result) if result else 0,
                }
            else:
                return {"success": False, "error": "No references response"}

        except Exception as e:
            logger.error(f"Error getting references: {e}")
            return {"success": False, "error": str(e)}

    async def get_document_symbols(self, file_path: str) -> Dict[str, Any]:
        """Get all symbols in a document"""
        try:
            logger.info(f"Getting document symbols for {file_path}")

            if not await self.lsp_service.initialize_session():
                return {"success": False, "error": "Failed to initialize LSP session"}

            if not await self.lsp_service.open_document(file_path):
                return {"success": False, "error": f"Failed to open document: {file_path}"}

            params = {"textDocument": {"uri": self.lsp_service._file_to_uri(file_path)}}

            response = await self.lsp_service._send_request("textDocument/documentSymbol", params)
            await self.lsp_service.close_document(file_path)

            if response and "result" in response:
                result = response["result"]
                return {
                    "success": True,
                    "file": file_path,
                    "symbols": self._process_document_symbols(result),
                    "total_symbols": len(result) if result else 0,
                }
            else:
                return {"success": False, "error": "No symbols response"}

        except Exception as e:
            logger.error(f"Error getting document symbols: {e}")
            return {"success": False, "error": str(e)}

    async def get_workspace_symbols(self, query: str = "", limit: int = 50) -> Dict[str, Any]:
        """Get workspace symbols matching query"""
        try:
            logger.info(f"Getting workspace symbols with query: '{query}'")

            if not await self.lsp_service.initialize_session():
                return {"success": False, "error": "Failed to initialize LSP session"}

            params = {"query": query}

            response = await self.lsp_service._send_request("workspace/symbol", params)

            if response and "result" in response:
                result = response["result"]
                limited_result = result[:limit] if result else []

                return {
                    "success": True,
                    "symbols": self._process_workspace_symbols(limited_result),
                    "total_found": len(result) if result else 0,
                    "returned": len(limited_result),
                    "query": query,
                }
            else:
                return {"success": False, "error": "No workspace symbols response"}

        except Exception as e:
            logger.error(f"Error getting workspace symbols: {e}")
            return {"success": False, "error": str(e)}

    # ------------------------
    # Internal processing helpers
    # ------------------------

    def _process_hover_result(self, hover_result: Dict[str, Any]) -> Dict[str, Any]:
        """Process hover result into readable format"""
        contents = hover_result.get("contents", {})

        if isinstance(contents, str):
            return {"content": contents, "format": "plaintext"}
        elif isinstance(contents, dict):
            return {
                "content": contents.get("value", ""),
                "format": contents.get("kind", "plaintext"),
            }
        elif isinstance(contents, list) and contents:
            first_item = contents[0]
            if isinstance(first_item, str):
                return {"content": first_item, "format": "plaintext"}
            elif isinstance(first_item, dict):
                return {
                    "content": first_item.get("value", ""),
                    "format": first_item.get("kind", "plaintext"),
                }

        return {"content": str(contents), "format": "plaintext"}

    def _process_completion_result(self, completion_result: Any) -> List[Dict[str, Any]]:
        """Process completion result"""
        if isinstance(completion_result, dict) and "items" in completion_result:
            items = completion_result["items"]
        elif isinstance(completion_result, list):
            items = completion_result
        else:
            return []

        processed_items = []
        for item in items:
            processed_items.append(
                {
                    "label": item.get("label", ""),
                    "kind": self._completion_kind_to_string(item.get("kind", 1)),
                    "detail": item.get("detail", ""),
                    "documentation": item.get("documentation", ""),
                    "insertText": item.get("insertText", item.get("label", "")),
                    "sortText": item.get("sortText", ""),
                }
            )

        return processed_items

    def _process_location_result(self, locations: Any) -> List[Dict[str, Any]]:
        """Process location results (for definitions/references)"""
        if not locations:
            return []

        if not isinstance(locations, list):
            locations = [locations]

        processed_locations = []
        for location in locations:
            uri = location.get("uri", "")
            range_info = location.get("range", {})
            start = range_info.get("start", {})
            end = range_info.get("end", {})

            file_path = self.lsp_service._uri_to_path(uri)
            relative_path = file_path.replace(self.lsp_service.workspace_path, "").lstrip("/")

            processed_locations.append(
                {
                    "file": relative_path,
                    "uri": uri,
                    "range": {
                        "start": {"line": start.get("line", 0) + 1, "character": start.get("character", 0) + 1},
                        "end": {"line": end.get("line", 0) + 1, "character": end.get("character", 0) + 1},
                    },
                }
            )

        return processed_locations

    def _process_document_symbols(self, symbols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process document symbols"""
        if not symbols:
            return []

        processed_symbols = []
        for symbol in symbols:
            processed_symbol = {
                "name": symbol.get("name", ""),
                "kind": self._symbol_kind_to_string(symbol.get("kind", 1)),
                "detail": symbol.get("detail", ""),
                "range": self._process_range(symbol.get("range", {})),
                "selectionRange": self._process_range(symbol.get("selectionRange", {})),
            }

            children = symbol.get("children", [])
            if children:
                processed_symbol["children"] = self._process_document_symbols(children)

            processed_symbols.append(processed_symbol)

        return processed_symbols

    def _process_workspace_symbols(self, symbols: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process workspace symbols"""
        if not symbols:
            return []

        processed_symbols = []
        for symbol in symbols:
            location = symbol.get("location", {})
            uri = location.get("uri", "")
            file_path = self.lsp_service._uri_to_path(uri)
            relative_path = file_path.replace(self.lsp_service.workspace_path, "").lstrip("/")

            processed_symbols.append(
                {
                    "name": symbol.get("name", ""),
                    "kind": self._symbol_kind_to_string(symbol.get("kind", 1)),
                    "file": relative_path,
                    "containerName": symbol.get("containerName"),
                    "location": {"file": relative_path, "range": self._process_range(location.get("range", {}))},
                }
            )

        return processed_symbols

    def _process_range(self, range_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process range information"""
        start = range_info.get("start", {})
        end = range_info.get("end", {})

        return {
            "start": {"line": start.get("line", 0) + 1, "character": start.get("character", 0) + 1},
            "end": {"line": end.get("line", 0) + 1, "character": end.get("character", 0) + 1},
        }

    def _symbol_kind_to_string(self, kind: int) -> str:
        """Convert symbol kind number to string"""
        kinds = {
            1: "file",
            2: "module",
            3: "namespace",
            4: "package",
            5: "class",
            6: "method",
            7: "property",
            8: "field",
            9: "constructor",
            10: "enum",
            11: "interface",
            12: "function",
            13: "variable",
            14: "constant",
            15: "string",
            16: "number",
            17: "boolean",
            18: "array",
            19: "object",
            20: "key",
            21: "null",
            22: "enumMember",
            23: "struct",
            24: "event",
            25: "operator",
            26: "typeParameter",
        }
        return kinds.get(kind, "unknown")

    def _completion_kind_to_string(self, kind: int) -> str:
        """Convert completion kind number to string"""
        kinds = {
            1: "text",
            2: "method",
            3: "function",
            4: "constructor",
            5: "field",
            6: "variable",
            7: "class",
            8: "interface",
            9: "module",
            10: "property",
            11: "unit",
            12: "value",
            13: "enum",
            14: "keyword",
            15: "snippet",
            16: "color",
            17: "file",
            18: "reference",
            19: "folder",
            20: "enumMember",
            21: "constant",
            22: "struct",
            23: "event",
            24: "operator",
            25: "typeParameter",
        }
        return kinds.get(kind, "text")
