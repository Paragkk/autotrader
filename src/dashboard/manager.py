"""
Dashboard Manager for AutoTrader Pro
Handles starting/stopping the Streamlit dashboard independently
"""

import logging
import os
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class DashboardManager:
    """Manages the Streamlit dashboard process"""

    def __init__(self, dashboard_port: int = 8501, api_base_url: str = "http://localhost:8080") -> None:
        self.dashboard_port = dashboard_port
        self.api_base_url = api_base_url
        self.dashboard_process: subprocess.Popen | None = None
        self.dashboard_path = Path(__file__).parent / "main.py"

    def start_dashboard(self) -> bool:
        """Start the Streamlit dashboard"""
        try:
            if self.is_running():
                logger.info(f"Dashboard already running on port {self.dashboard_port}")
                return True

            logger.info("Starting Streamlit Dashboard...")

            # Set environment variable for API base URL
            env = os.environ.copy()
            env["AUTOTRADER_API_BASE_URL"] = self.api_base_url
            # Set UTF-8 encoding to handle console output properly
            env["PYTHONIOENCODING"] = "utf-8"

            # Log the command we're about to run
            cmd = [
                "uv",
                "run",
                "streamlit",
                "run",
                str(self.dashboard_path),
                "--server.port",
                str(self.dashboard_port),
                "--server.address",
                "0.0.0.0",
                "--theme.base",
                "dark",
                "--server.headless",
                "true",
                "--browser.gatherUsageStats",
                "false",
                "--server.enableXsrfProtection",
                "false",
            ]
            logger.info(f"Dashboard command: {' '.join(cmd)}")
            logger.info(f"Dashboard path: {self.dashboard_path}")
            logger.info(f"Dashboard path exists: {self.dashboard_path.exists()}")

            # Start dashboard in background using uv
            # Capture output for debugging
            self.dashboard_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,  # Provide stdin to handle email prompt
                env=env,
                cwd=Path(__file__).parent.parent.parent,  # Set working directory to project root
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Send empty line to bypass email prompt if it appears
            if self.dashboard_process.stdin:
                try:
                    self.dashboard_process.stdin.write("\n")
                    self.dashboard_process.stdin.flush()
                    self.dashboard_process.stdin.close()
                except Exception as e:
                    logger.debug(f"Could not send input to dashboard process: {e}")

            # Wait for dashboard to start
            logger.info("Waiting for dashboard to start...")
            time.sleep(5)

            # Check if process is still running and capture any error output
            if self.dashboard_process.poll() is None:
                logger.info(f"Dashboard started successfully at http://localhost:{self.dashboard_port}")
                # Additional check - try to ping the dashboard
                try:
                    import requests

                    response = requests.get(f"http://localhost:{self.dashboard_port}", timeout=5)
                    if response.status_code == 200:
                        logger.info("Dashboard is responding to HTTP requests")
                    else:
                        logger.warning(f"Dashboard process running but HTTP status: {response.status_code}")
                except Exception as e:
                    logger.warning(f"Dashboard process running but HTTP check failed: {e}")
                return True
            logger.error("Dashboard process ended unexpectedly")
            # Try to capture any error output
            try:
                stdout, stderr = self.dashboard_process.communicate(timeout=1)
                if stdout:
                    logger.error(f"Dashboard stdout: {stdout}")
                if stderr:
                    logger.error(f"Dashboard stderr: {stderr}")
            except subprocess.TimeoutExpired:
                logger.exception("Could not capture dashboard output - process timeout")
            except Exception as e:
                logger.exception(f"Error capturing dashboard output: {e}")

            self.dashboard_process = None
            return False

        except Exception as e:
            logger.exception(f"Failed to start dashboard: {e}")
            self.dashboard_process = None
            return False

    def stop_dashboard(self) -> bool:
        """Stop the Streamlit dashboard"""
        try:
            if not self.is_running():
                logger.info("Dashboard is not running")
                return True

            logger.info("Stopping Streamlit Dashboard...")

            if self.dashboard_process:
                self.dashboard_process.terminate()

                # Wait for graceful shutdown
                try:
                    self.dashboard_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    self.dashboard_process.kill()
                    self.dashboard_process.wait()

                self.dashboard_process = None

            logger.info("Dashboard stopped successfully")
            return True

        except Exception as e:
            logger.exception(f"Failed to stop dashboard: {e}")
            return False

    def is_running(self) -> bool:
        """Check if dashboard is currently running"""
        if self.dashboard_process is None:
            return False

        return self.dashboard_process.poll() is None

    def restart_dashboard(self) -> bool:
        """Restart the dashboard"""
        logger.info("Restarting dashboard...")
        self.stop_dashboard()
        time.sleep(2)
        return self.start_dashboard()

    def get_status(self) -> dict:
        """Get dashboard status information"""
        return {
            "running": self.is_running(),
            "port": self.dashboard_port,
            "url": f"http://localhost:{self.dashboard_port}",
            "api_base_url": self.api_base_url,
            "process_id": self.dashboard_process.pid if self.dashboard_process else None,
        }
