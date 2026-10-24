from __future__ import annotations

from pathlib import Path

from mcp_service.config import FILESYSTEM_ROOT
from mcp_service.logging_utils import get_logger


logger = get_logger(__name__)


def _resolve_safe_path(directory: str) -> Path:
    """
    Resolve a user-provided path inside the configured project root.

    Relative paths are resolved from the project root.
    Absolute paths are accepted only when they are inside the project root.
    """

    requested = Path(directory).expanduser()

    if requested.is_absolute():
        candidate = requested.resolve()
    else:
        candidate = (FILESYSTEM_ROOT / requested).resolve()

    try:
        candidate.relative_to(FILESYSTEM_ROOT)
    except ValueError as error:
        raise ValueError(
            f"Access is limited to the project directory: {FILESYSTEM_ROOT}"
        ) from error

    return candidate


def list_directory(
    directory: str,
    recursive: bool = False,
    extension: str | None = None,
) -> dict:
    """
    List files and folders inside the LangGraph_MCP_Agent project.

    directory:
        Relative path such as '.', 'backend', 'mcp_service',
        'mcp_service', 'logs', or 'mcp_service/tools'.

    recursive:
        If True, include all nested files and directories.

    extension:
        Optional file extension filter such as 'py', 'md', or 'json'.
    """

    try:
        logger.info(
            "Filesystem listing started directory=%s recursive=%s extension=%s",
            directory,
            recursive,
            extension or "none",
        )

        path = _resolve_safe_path(directory)

        if not path.exists():
            logger.warning(
                "Filesystem listing failed reason=missing_directory directory=%s",
                directory,
            )
            return {
                "ok": False,
                "error": f"Directory does not exist: {directory}",
                "entries": [],
            }

        if not path.is_dir():
            logger.warning(
                "Filesystem listing failed reason=not_directory directory=%s",
                directory,
            )
            return {
                "ok": False,
                "error": f"Path is not a directory: {directory}",
                "entries": [],
            }

        iterator = path.rglob("*") if recursive else path.iterdir()

        suffix = extension.lower().lstrip(".") if extension else None

        entries = []

        for item in sorted(iterator, key=lambda value: str(value).lower()):

            if suffix:
                if item.is_file() and item.suffix.lower() != f".{suffix}":
                    continue

                if item.is_dir():
                    continue

            stat = item.stat()

            entries.append(
                {
                    "path": str(item.relative_to(FILESYSTEM_ROOT)),
                    "type": "directory" if item.is_dir() else "file",
                    "size_bytes": None if item.is_dir() else stat.st_size,
                    "modified_at": stat.st_mtime,
                }
            )

        logger.info(
            "Filesystem listing completed directory=%s entry_count=%d",
            directory,
            len(entries),
        )

        return {
            "ok": True,
            "directory": str(path.relative_to(FILESYSTEM_ROOT)),
            "entries": entries,
        }

    except (OSError, ValueError) as error:

        logger.warning(
            "Filesystem listing failed directory=%s error=%s",
            directory,
            error,
        )

        return {
            "ok": False,
            "error": str(error),
            "entries": [],
        }
