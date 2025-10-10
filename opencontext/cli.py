# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Command-line interface - provides the entry point for command-line tools
"""

import argparse
import sys
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import Optional

from fastapi.staticfiles import StaticFiles
import uvicorn

from opencontext.server.opencontext import OpenContext
from opencontext.server.api import router as api_router
from opencontext.config.config_manager import ConfigManager
from opencontext.utils.logging_utils import setup_logging, get_logger

logger = get_logger(__name__)

# Global variables for multi-process support
_config_path = None
_context_lab_instance = None

def get_or_create_context_lab():
    """Get or create the global OpenContext instance for the current process."""
    global _context_lab_instance, _config_path
    if _context_lab_instance is None:
        _context_lab_instance = _initialize_context_lab(_config_path)
        _context_lab_instance.initialize()
        _context_lab_instance.start_capture()
    return _context_lab_instance

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI."""
    # Startup
    if not hasattr(app.state, 'context_lab_instance'):
        app.state.context_lab_instance = get_or_create_context_lab()
    yield
    # Shutdown - cleanup if needed
    pass

app = FastAPI(title="OpenContext", version="1.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Project root
if hasattr(sys, '_MEIPASS'):
    project_root = Path(sys._MEIPASS)
else:
    project_root = Path(__file__).parent.parent.parent.resolve()

def _get_project_root() -> Path:
    """Get the project root directory."""
    return project_root

def _setup_static_files() -> None:
    """Setup static file mounts for the FastAPI app."""
    # Mount static files
    if hasattr(sys, '_MEIPASS'):
        static_path = Path(sys._MEIPASS) / "opencontext/web/static"
    else:
        static_path = Path(__file__).parent / "web/static"
    
    print(f"Static path: {static_path}")
    print(f"Static path exists: {static_path.exists()}")
    print(f"Static path absolute: {static_path.resolve()}")
    
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
        print(f"Mounted static files from: {static_path}")
    else:
        print(f"Static path does not exist: {static_path}")
    
    # Mount screenshots directory
    screenshots_path = Path("./screenshots").resolve()
    if screenshots_path.exists():
        app.mount("/screenshots", StaticFiles(directory=screenshots_path), name="screenshots")

_setup_static_files()

app.include_router(api_router)

def start_web_server(context_lab_instance: OpenContext, host: str, port: int, workers: int = 1, config_path: str = None) -> None:
    """Start the web server with the given opencontext instance.
    
    Args:
        context_lab_instance: The opencontext instance to attach to the app
        host: Host address to bind to
        port: Port number to bind to
        workers: Number of worker processes
        config_path: Configuration file path for multi-process mode
    """
    global _config_path
    _config_path = config_path
    
    if workers > 1:
        logger.info(f"Starting with {workers} worker processes")
        # For multi-process mode, use import string to avoid the warning
        uvicorn.run("opencontext.cli:app", host=host, port=port, log_level="info", workers=workers)
    else:
        # For single process mode, use the existing instance
        app.state.context_lab_instance = context_lab_instance
        uvicorn.run(app, host=host, port=port, log_level="info")

def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description="OpenContext - Context capture, processing, storage and consumption system"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start OpenContext server")
    start_parser.add_argument(
        "--config",
        type=str,
        help="Configuration file path"
    )
    start_parser.add_argument(
        "--host",
        type=str,
        help="Host address (overrides config file)"
    )
    start_parser.add_argument(
        "--port",
        type=int,
        help="Port number (overrides config file)"
    )
    start_parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )

    return parser.parse_args()


def _initialize_context_lab(config_path: Optional[str]) -> OpenContext:
    """Initialize the OpenContext instance.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Initialized OpenContext instance
        
    Raises:
        RuntimeError: If initialization fails
    """
    try:
        lab_instance = OpenContext(config_path=config_path)
        lab_instance.initialize()
        return lab_instance
    except Exception as e:
        logger.error(f"Failed to initialize OpenContext: {e}")
        raise RuntimeError(f"OpenContext initialization failed: {e}") from e

def _run_headless_mode(lab_instance: OpenContext) -> None:
    """Run in headless mode without web server.
    
    Args:
        lab_instance: The opencontext instance
    """
    try:
        logger.info("Running in headless mode. Press Ctrl+C to exit.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        lab_instance.shutdown()

def handle_start(args: argparse.Namespace) -> int:
    """Handle the start command.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        lab_instance = _initialize_context_lab(args.config)
    except RuntimeError:
        return 1

    logger.info("Starting all modules")
    lab_instance.start_capture()

    from opencontext.config.global_config import get_config
    web_config = get_config("web")
    if web_config.get("enabled", True):
        # Command line arguments override config file
        host = args.host if args.host else web_config.get("host", "localhost")
        port = args.port if args.port else web_config.get("port", 8000)

        try:
            logger.info(f"Starting web server on {host}:{port}")
            workers = getattr(args, 'workers', 1)
            start_web_server(lab_instance, host, port, workers, args.config)
        finally:
            logger.info("Web server closed, shutting down capture modules...")
            lab_instance.shutdown()
    else:
        _run_headless_mode(lab_instance)

    return 0
def _setup_logging(config_path: Optional[str]) -> None:
    """Setup logging configuration.
    
    Args:
        config_path: Optional path to configuration file
    """
    from opencontext.config.global_config import GlobalConfig
    GlobalConfig.get_instance().initialize(config_path)

    setup_logging(GlobalConfig.get_instance().get_config('logging'))

def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    args = parse_args()

    # Setup logging first
    _setup_logging(getattr(args, 'config', None))

    logger.debug(f"Command line arguments: {args}")

    if not args.command:
        logger.error("No command specified. Use 'opencontext start' or 'opencontext --help' for usage.")
        return 1

    if args.command == "start":
        return handle_start(args)
    else:
        logger.error(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())