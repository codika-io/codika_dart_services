"""
Core Dart Language Server Protocol (LSP) Service
Handles low-level communication with the Dart analyzer server
File: codika_dart_analyzer/dart_lsp_service.py
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DartLSPService:
    """Core service for communicating with Dart Language Server via LSP protocol"""

    def __init__(self, host: str = "127.0.0.1", port: int = 8081):
        self.host = host
        self.port = port
        self.request_id = 1
        self._initialized = False
        self.workspace_path = "/opt/codika/persistent/user-app"

    async def _create_connection(self, timeout: float = 5.0) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Create a connection to the LSP server"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=timeout,
            )
            logger.debug(f"Connected to Dart LSP server at {self.host}:{self.port}")
            return reader, writer
        except Exception as e:
            logger.error(f"Failed to connect to LSP server: {e}")
            raise ConnectionError(
                f"Could not connect to Dart analyzer on {self.host}:{self.port}"
            )

    async def _send_message(self, writer: asyncio.StreamWriter, message: Dict[str, Any]) -> None:
        """Send an LSP message with proper Content-Length header"""
        content = json.dumps(message)
        content_bytes = content.encode("utf-8")
        header = f"Content-Length: {len(content_bytes)}\r\n\r\n"

        writer.write(header.encode("utf-8"))
        writer.write(content_bytes)
        await writer.drain()

        logger.debug(f"Sent LSP message: {message.get('method', 'response')}")

    async def _receive_message(self, reader: asyncio.StreamReader, timeout: float = 10.0) -> Optional[Dict[str, Any]]:
        """Receive an LSP message"""
        try:
            # Read header
            header = b""
            while b"\r\n\r\n" not in header:
                chunk = await asyncio.wait_for(reader.read(1), timeout=timeout)
                if not chunk:
                    return None
                header += chunk

            # Parse content length
            header_str = header.decode("utf-8")
            content_length = 0
            for line in header_str.split("\r\n"):
                if line.startswith("Content-Length:"):
                    content_length = int(line.split(":")[1].strip())
                    break

            if content_length == 0:
                return None

            # Read content
            content = await asyncio.wait_for(reader.read(content_length), timeout=timeout)
            response = json.loads(content.decode("utf-8"))

            logger.debug(f"Received LSP message: {response.get('method', 'response')}")
            return response

        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for LSP response")
            return None
        except Exception as e:
            logger.error(f"Error receiving LSP message: {e}")
            return None

    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Send a request and wait for response"""
        message = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {},
        }

        self.request_id += 1

        try:
            reader, writer = await self._create_connection()
            try:
                await self._send_message(writer, message)
                response = await self._receive_message(reader)
                return response
            finally:
                writer.close()
                await writer.wait_closed()
        except Exception as e:
            logger.error(f"Error sending LSP request {method}: {e}")
            return None

    async def _send_notification(self, method: str, params: Dict[str, Any] = None) -> bool:
        """Send a notification (no response expected)"""
        message = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }

        try:
            reader, writer = await self._create_connection()
            try:
                await self._send_message(writer, message)
                return True
            finally:
                writer.close()
                await writer.wait_closed()
        except Exception as e:
            logger.error(f"Error sending LSP notification {method}: {e}")
            return False

    async def test_connection(self) -> bool:
        """Test if the LSP server is accessible"""
        try:
            reader, writer = await self._create_connection(timeout=3.0)
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def initialize_session(self) -> bool:
        """Initialize LSP session with the server"""
        if self._initialized:
            return True

        # Check if workspace exists
        if not Path(self.workspace_path).exists():
            logger.error(f"Workspace path does not exist: {self.workspace_path}")
            return False

        params = {
            "processId": None,
            "clientInfo": {
                "name": "CodikaAnalyzer",
                "version": "1.0.0",
            },
            "rootUri": f"file://{self.workspace_path}",
            "capabilities": {
                "textDocument": {
                    "publishDiagnostics": {
                        "relatedInformation": True,
                        "versionSupport": False,
                        "codeDescriptionSupport": True,
                    },
                    "hover": {"contentFormat": ["markdown", "plaintext"]},
                    "completion": {"completionItem": {"snippetSupport": True}},
                    "definition": {"linkSupport": True},
                    "references": {"context": True},
                    "documentSymbol": {"hierarchicalDocumentSymbolSupport": True},
                },
                "workspace": {
                    "symbol": {"symbolKind": {"valueSet": list(range(1, 27))}},
                    "workspaceEdit": {"documentChanges": True},
                },
            },
        }

        response = await self._send_request("initialize", params)
        if response and "result" in response:
            # Send initialized notification
            await self._send_notification("initialized", {})
            self._initialized = True
            logger.info("LSP session initialized successfully")
            return True

        logger.error("Failed to initialize LSP session")
        return False

    async def open_document(self, file_path: str) -> bool:
        """Open a document for analysis"""
        try:
            abs_path = Path(file_path)
            if not abs_path.is_absolute():
                abs_path = Path(self.workspace_path) / file_path

            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()

            params = {
                "textDocument": {
                    "uri": f"file://{abs_path}",
                    "languageId": "dart",
                    "version": 1,
                    "text": content,
                }
            }

            return await self._send_notification("textDocument/didOpen", params)

        except Exception as e:
            logger.error(f"Error opening document {file_path}: {e}")
            return False

    async def close_document(self, file_path: str) -> bool:
        """Close a document"""
        try:
            abs_path = Path(file_path)
            if not abs_path.is_absolute():
                abs_path = Path(self.workspace_path) / file_path

            params = {
                "textDocument": {"uri": f"file://{abs_path}"}
            }

            return await self._send_notification("textDocument/didClose", params)

        except Exception as e:
            logger.error(f"Error closing document {file_path}: {e}")
            return False

    def _file_to_uri(self, file_path: str) -> str:
        """Convert file path to URI"""
        abs_path = Path(file_path)
        if not abs_path.is_absolute():
            abs_path = Path(self.workspace_path) / file_path
        return f"file://{abs_path}"

    def _uri_to_path(self, uri: str) -> str:
        """Convert URI to file path"""
        return uri.replace("file://", "") 