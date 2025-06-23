"""
Dart Workspace Service
Handles workspace and project management functionality
File: codika_dart_analyzer/dart_workspace_service.py
"""

import yaml
import logging
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

from .dart_lsp_service import DartLSPService

logger = logging.getLogger(__name__)


class DartWorkspaceService:
    """Service for workspace and project management"""

    def __init__(self, lsp_service: DartLSPService = None):
        self.lsp_service = lsp_service or DartLSPService()
        self.workspace_path = Path(self.lsp_service.workspace_path)

    async def get_workspace_info(self) -> Dict[str, Any]:
        """Get comprehensive workspace information"""
        try:
            if not self.workspace_path.exists():
                return {
                    "success": False,
                    "error": "Workspace directory does not exist",
                    "path": str(self.workspace_path),
                }

            # Get project info
            project_info = await self._get_project_info()

            # Get file structure
            file_structure = await self._get_file_structure()

            # Get Dart files count
            dart_files = await self._get_dart_files()

            return {
                "success": True,
                "workspace_path": str(self.workspace_path),
                "project_info": project_info,
                "file_structure": file_structure,
                "dart_files_count": len(dart_files),
                "dart_files": dart_files[:20],  # Limit to first 20 for response size
                "total_dart_files": len(dart_files),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting workspace info: {e}")
            return {
                "success": False,
                "error": str(e),
                "workspace_path": str(self.workspace_path),
            }

    async def get_dart_files(self, include_generated: bool = False) -> Dict[str, Any]:
        """Get list of all Dart files in workspace"""
        try:
            dart_files = []

            if not self.workspace_path.exists():
                return {"success": False, "error": "Workspace directory does not exist"}

            for dart_file in self.workspace_path.rglob("*.dart"):
                # Skip generated files and build directories unless requested
                if not include_generated:
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

                relative_path = str(dart_file.relative_to(self.workspace_path))
                dart_files.append(
                    {
                        "path": relative_path,
                        "full_path": str(dart_file),
                        "size": dart_file.stat().st_size,
                        "modified": datetime.fromtimestamp(
                            dart_file.stat().st_mtime
                        ).isoformat(),
                    }
                )

            return {
                "success": True,
                "files": sorted(dart_files, key=lambda x: x["path"]),
                "total_files": len(dart_files),
                "include_generated": include_generated,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting Dart files: {e}")
            return {"success": False, "error": str(e)}

    async def validate_workspace(self) -> Dict[str, Any]:
        """Validate workspace structure and dependencies"""
        try:
            validation_results = {
                "success": True,
                "issues": [],
                "warnings": [],
                "info": [],
            }

            # Check if workspace exists
            if not self.workspace_path.exists():
                validation_results["success"] = False
                validation_results["issues"].append("Workspace directory does not exist")
                return validation_results

            # Check for pubspec.yaml
            pubspec_path = self.workspace_path / "pubspec.yaml"
            if not pubspec_path.exists():
                validation_results["issues"].append("pubspec.yaml not found")
                validation_results["success"] = False
            else:
                validation_results["info"].append("pubspec.yaml found")

                # Validate pubspec.yaml content
                try:
                    with open(pubspec_path, "r") as f:
                        pubspec_data = yaml.safe_load(f)

                    if not pubspec_data.get("name"):
                        validation_results["issues"].append(
                            "Project name not specified in pubspec.yaml"
                        )

                    if not pubspec_data.get("dependencies"):
                        validation_results["warnings"].append("No dependencies specified")

                    flutter_dep = pubspec_data.get("dependencies", {}).get("flutter")
                    if not flutter_dep:
                        validation_results["warnings"].append("Flutter dependency not found")

                except Exception as e:
                    validation_results["issues"].append(
                        f"Error parsing pubspec.yaml: {e}"
                    )

            # Check for lib directory
            lib_path = self.workspace_path / "lib"
            if not lib_path.exists():
                validation_results["issues"].append("lib directory not found")
            else:
                validation_results["info"].append("lib directory found")

                # Check for main.dart
                main_dart = lib_path / "main.dart"
                if not main_dart.exists():
                    validation_results["warnings"].append(
                        "main.dart not found in lib directory"
                    )
                else:
                    validation_results["info"].append("main.dart found")

            # Check for analysis_options.yaml
            analysis_options = self.workspace_path / "analysis_options.yaml"
            if not analysis_options.exists():
                validation_results["warnings"].append(
                    "analysis_options.yaml not found"
                )
            else:
                validation_results["info"].append("analysis_options.yaml found")

            # Check .dart_tool directory
            dart_tool = self.workspace_path / ".dart_tool"
            if not dart_tool.exists():
                validation_results["warnings"].append(
                    ".dart_tool directory not found - run 'flutter pub get'"
                )
            else:
                validation_results["info"].append(".dart_tool directory found")

            # Set overall success based on critical issues
            if validation_results["issues"]:
                validation_results["success"] = False

            validation_results["summary"] = {
                "critical_issues": len(validation_results["issues"]),
                "warnings": len(validation_results["warnings"]),
                "info_items": len(validation_results["info"]),
            }

            return validation_results

        except Exception as e:
            logger.error(f"Error validating workspace: {e}")
            return {
                "success": False,
                "error": str(e),
                "issues": [str(e)],
            }

    async def refresh_workspace(self) -> Dict[str, Any]:
        """Refresh workspace analysis"""
        try:
            logger.info("Refreshing workspace analysis")

            # Check if LSP server is available
            if not await self.lsp_service.test_connection():
                return {
                    "success": False,
                    "error": "Dart analyzer server is not available",
                }

            # Re-initialize LSP session
            if await self.lsp_service.initialize_session():
                return {
                    "success": True,
                    "message": "Workspace analysis refreshed successfully",
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to initialize LSP session for refresh",
                }

        except Exception as e:
            logger.error(f"Error refreshing workspace: {e}")
            return {"success": False, "error": str(e)}

    async def _get_project_info(self) -> Dict[str, Any]:
        """Get project information from pubspec.yaml"""
        try:
            pubspec_path = self.workspace_path / "pubspec.yaml"

            if not pubspec_path.exists():
                return {"error": "pubspec.yaml not found"}

            with open(pubspec_path, "r") as f:
                pubspec_data = yaml.safe_load(f)

            # Extract key information
            project_info = {
                "name": pubspec_data.get("name", "Unknown"),
                "description": pubspec_data.get("description", ""),
                "version": pubspec_data.get("version", ""),
                "homepage": pubspec_data.get("homepage", ""),
                "repository": pubspec_data.get("repository", ""),
            }

            # Dependencies info
            dependencies = pubspec_data.get("dependencies", {})
            dev_dependencies = pubspec_data.get("dev_dependencies", {})

            project_info["dependencies"] = {
                "production": list(dependencies.keys()),
                "development": list(dev_dependencies.keys()),
                "total_dependencies": len(dependencies) + len(dev_dependencies),
            }

            # Flutter info
            flutter_constraint = pubspec_data.get("environment", {}).get("flutter")
            dart_constraint = pubspec_data.get("environment", {}).get("sdk")

            project_info["environment"] = {
                "flutter_constraint": flutter_constraint,
                "dart_constraint": dart_constraint,
            }

            return project_info

        except Exception as e:
            logger.error(f"Error getting project info: {e}")
            return {"error": str(e)}

    async def _get_file_structure(self) -> Dict[str, Any]:
        """Get workspace file structure overview"""
        try:
            structure = {
                "directories": [],
                "files": [],
                "total_files": 0,
                "total_directories": 0,
            }

            for item in self.workspace_path.iterdir():
                if item.is_dir():
                    # Skip hidden directories and common build directories
                    if item.name.startswith(".") or item.name in ["build"]:
                        continue

                    dir_info = {
                        "name": item.name,
                        "path": str(item.relative_to(self.workspace_path)),
                        "file_count": len(list(item.rglob("*"))),
                    }
                    structure["directories"].append(dir_info)
                    structure["total_directories"] += 1
                else:
                    file_info = {
                        "name": item.name,
                        "path": str(item.relative_to(self.workspace_path)),
                        "size": item.stat().st_size,
                        "extension": item.suffix,
                    }
                    structure["files"].append(file_info)
                    structure["total_files"] += 1

            return structure

        except Exception as e:
            logger.error(f"Error getting file structure: {e}")
            return {"error": str(e)}

    async def _get_dart_files(self) -> List[str]:
        """Get list of Dart files"""
        dart_files = []

        if not self.workspace_path.exists():
            return dart_files

        for dart_file in self.workspace_path.rglob("*.dart"):
            # Skip generated files and build directories
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

            relative_path = str(dart_file.relative_to(self.workspace_path))
            dart_files.append(relative_path)

        return sorted(dart_files) 