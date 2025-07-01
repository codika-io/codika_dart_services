import logging
from pathlib import Path

from . import DartDiagnosticsService, DartLSPService

from .errors import DartAnalyzerError

logger = logging.getLogger(__name__)

# Global instances - reused across calls for efficiency and LSP session persistence
lsp_service = DartLSPService()
diagnostics_service = DartDiagnosticsService(lsp_service)

async def _ensure_initialized():
    """Ensure LSP session is initialized before use"""
    if not lsp_service._initialized:
        success = await lsp_service.initialize_session()
        if not success:
            raise DartAnalyzerError(
                message="Failed to initialize Dart LSP session"
            )

async def analyze_dart_code(
    project_path: str | Path,
    markdown: bool = True,
    timeout: int = 30
) -> str:
    """
    Use the DartDiagnosticsService to analyze the project.
    
    Args:
        project_path: Path to the project root directory
        markdown: Whether to wrap output in markdown code block
        timeout: Optional timeout in seconds for the analysis
        
    Returns:
        The output of the dart analyze command
        
    Raises:
        DartAnalyzerError: If the command fails to execute
    """
    try:
        # Ensure LSP session is initialized before analysis
        await _ensure_initialized()
        
        result = await diagnostics_service.analyze_project(timeout=timeout)
        return result if not markdown else f"```{result}```"
    except Exception as e:
        logger.error(f"Error analyzing project: {e}")
        raise DartAnalyzerError(
            message=f"Failed to analyze code: {str(e)}",
        )