"""
Dart Diagnostics Service
Handles diagnostics, analysis, and code quality checks
File: codika_dart_analyzer/dart_diagnostics_service.py
"""

import asyncio
import logging
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

from .dart_lsp_service import DartLSPService

logger = logging.getLogger(__name__)


class DartDiagnosticsService:
    """Service for handling Dart code diagnostics and analysis"""

    def __init__(self, lsp_service: DartLSPService = None):
        self.lsp_service = lsp_service or DartLSPService()
        self._diagnostics_cache = {}
        self._last_analysis = None

    async def analyze_project(self, timeout: int = 30) -> Dict[str, Any]:
        """Analyze the entire project and return diagnostics"""
        try:
            logger.info("Starting project analysis")

            if not await self.lsp_service.initialize_session():
                return {
                    "success": False,
                    "error": "Failed to initialize LSP session",
                    "timestamp": datetime.now().isoformat(),
                }

            dart_files = await self._find_dart_files()
            if not dart_files:
                return {
                    "success": True,
                    "diagnostics": [],
                    "summary": {"errors": 0, "warnings": 0, "info": 0},
                    "message": "No Dart files found in project",
                    "timestamp": datetime.now().isoformat(),
                }

            logger.info(f"Found {len(dart_files)} Dart files to analyze")

            diagnostics_received = []
            reader, writer = await self.lsp_service._create_connection()

            try:
                for file_path in dart_files[:20]:
                    await self.lsp_service.open_document(file_path)
                    await asyncio.sleep(0.1)

                logger.info("Collecting diagnostics...")
                start_time = asyncio.get_event_loop().time()

                while (asyncio.get_event_loop().time() - start_time) < timeout:
                    try:
                        response = await self.lsp_service._receive_message(reader, timeout=2.0)
                        if response and response.get("method") == "textDocument/publishDiagnostics":
                            diagnostics_received.append(response)
                        elif not response:
                            break
                    except Exception as e:
                        logger.debug(f"Error receiving diagnostics: {e}")
                        break
            finally:
                writer.close()
                await writer.wait_closed()

            processed_diagnostics = self._process_diagnostics(diagnostics_received)
            self._diagnostics_cache = processed_diagnostics
            self._last_analysis = datetime.now()

            return {
                "success": True,
                "diagnostics": processed_diagnostics["diagnostics"],
                "summary": processed_diagnostics["summary"],
                "files_analyzed": len(dart_files),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error analyzing project: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a specific file"""
        try:
            logger.info(f"Analyzing file: {file_path}")

            if not await self.lsp_service.initialize_session():
                return {"success": False, "error": "Failed to initialize LSP session"}

            if not await self.lsp_service.open_document(file_path):
                return {"success": False, "error": f"Failed to open document: {file_path}"}

            reader, writer = await self.lsp_service._create_connection()
            try:
                diagnostics_received = []
                start_time = asyncio.get_event_loop().time()

                while (asyncio.get_event_loop().time() - start_time) < 10:
                    response = await self.lsp_service._receive_message(reader, timeout=2.0)
                    if response and response.get("method") == "textDocument/publishDiagnostics":
                        params = response.get("params", {})
                        uri = params.get("uri", "")
                        if file_path in uri or uri.endswith(file_path):
                            diagnostics_received.append(response)
                            break
                    elif not response:
                        break
            finally:
                writer.close()
                await writer.wait_closed()
                await self.lsp_service.close_document(file_path)

            if diagnostics_received:
                processed = self._process_diagnostics(diagnostics_received)
                return {
                    "success": True,
                    "file": file_path,
                    "diagnostics": processed["diagnostics"],
                    "summary": processed["summary"],
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                return {
                    "success": True,
                    "file": file_path,
                    "diagnostics": [],
                    "summary": {"errors": 0, "warnings": 0, "info": 0},
                    "message": "No diagnostics found",
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return {"success": False, "error": str(e), "file": file_path}

    async def get_cached_diagnostics(self) -> Dict[str, Any]:
        """Get cached diagnostics from last analysis"""
        if not self._diagnostics_cache:
            return {
                "success": False,
                "message": "No cached diagnostics available. Run analysis first.",
                "timestamp": datetime.now().isoformat(),
            }

        return {
            "success": True,
            "diagnostics": self._diagnostics_cache.get("diagnostics", []),
            "summary": self._diagnostics_cache.get("summary", {}),
            "last_analysis": self._last_analysis.isoformat() if self._last_analysis else None,
            "timestamp": datetime.now().isoformat(),
        }

    async def get_diagnostics_summary(self) -> Dict[str, Any]:
        """Get summary of diagnostics"""
        if not self._diagnostics_cache:
            result = await self.analyze_project(timeout=15)
            if not result.get("success"):
                return result

        summary = self._diagnostics_cache.get("summary", {})
        return {
            "success": True,
            "summary": summary,
            "total_issues": summary.get("errors", 0) + summary.get("warnings", 0) + summary.get("info", 0),
            "last_analysis": self._last_analysis.isoformat() if self._last_analysis else None,
            "timestamp": datetime.now().isoformat(),
        }

    async def _find_dart_files(self) -> List[str]:
        """Find all Dart files in the workspace"""
        dart_files = []
        workspace = Path(self.lsp_service.workspace_path)

        if not workspace.exists():
            return []

        for dart_file in workspace.rglob("*.dart"):
            if any(
                skip in str(dart_file)
                for skip in [
                    ".dart_tool",
                    "build",
                    ".g.dart",
                    ".freezed.dart",
                ]
            ):
                continue
            dart_files.append(str(dart_file))

        return sorted(dart_files)

    def _process_diagnostics(self, diagnostics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process raw diagnostics into structured format"""
        processed_diagnostics = []
        total_errors = 0
        total_warnings = 0
        total_info = 0

        for diagnostic_msg in diagnostics_list:
            params = diagnostic_msg.get("params", {})
            uri = params.get("uri", "")
            diagnostics = params.get("diagnostics", [])
            if not diagnostics:
                continue

            file_path = self.lsp_service._uri_to_path(uri)
            relative_path = file_path.replace(self.lsp_service.workspace_path, "").lstrip("/")

            file_diagnostics = {"file": relative_path, "uri": uri, "issues": []}
            for diag in diagnostics:
                severity = diag.get("severity", 1)
                message = diag.get("message", "")
                range_info = diag.get("range", {})
                start = range_info.get("start", {})
                end = range_info.get("end", {})

                if severity == 1:
                    severity_text = "error"
                    total_errors += 1
                elif severity == 2:
                    severity_text = "warning"
                    total_warnings += 1
                elif severity == 3:
                    severity_text = "info"
                    total_info += 1
                else:
                    severity_text = "hint"
                    total_info += 1

                issue = {
                    "severity": severity_text,
                    "message": message,
                    "line": start.get("line", 0) + 1,
                    "character": start.get("character", 0) + 1,
                    "endLine": end.get("line", 0) + 1,
                    "endCharacter": end.get("character", 0) + 1,
                    "code": diag.get("code"),
                    "source": diag.get("source", "dart"),
                }

                file_diagnostics["issues"].append(issue)

            if file_diagnostics["issues"]:
                processed_diagnostics.append(file_diagnostics)

        return {
            "diagnostics": processed_diagnostics,
            "summary": {
                "errors": total_errors,
                "warnings": total_warnings,
                "info": total_info,
                "files_with_issues": len(processed_diagnostics),
            },
        } 