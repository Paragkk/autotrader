"""
Dashboard Manager for AutoTrader Pro
Handles starting/stopping the Streamlit dashboard independently
"""

import logging
import os
import platform
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

    def _kill_process_on_port(self, port: int) -> bool:
        """Kill any process using the specified port"""
        try:
            if platform.system() == "Windows":
                return self._kill_process_on_port_windows(port)
            return self._kill_process_on_port_unix(port)
        except Exception as e:
            logger.warning(f"Failed to kill process on port {port}: {e}")
            return False

    def _kill_process_on_port_windows(self, port: int) -> bool:
        """Kill process on Windows using netstat and taskkill"""
        try:
            # Find process using the port
            result = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, check=True)

            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        logger.info(f"Found process {pid} using port {port}")
                        # Kill the process
                        kill_result = subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, text=True, check=False)
                        if kill_result.returncode == 0:
                            logger.info(f"Successfully killed process {pid}")
                            return True
                        logger.warning(f"Failed to kill process {pid}: {kill_result.stderr}")
            return False
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to run netstat: {e}")
            return False
        except Exception as e:
            logger.warning(f"Failed to kill process on Windows: {e}")
            return False

    def _kill_process_on_port_unix(self, port: int) -> bool:
        """Kill process on Unix-like systems using lsof and kill"""
        try:
            # Find process using the port
            result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True, check=False)

            if result.stdout.strip():
                pid = result.stdout.strip()
                logger.info(f"Found process {pid} using port {port}")
                # Kill the process
                kill_result = subprocess.run(["kill", "-9", pid], capture_output=True, check=False)
                if kill_result.returncode == 0:
                    logger.info(f"Successfully killed process {pid}")
                    return True
                logger.warning(f"Failed to kill process {pid}")
            return False
        except Exception as e:
            logger.warning(f"Failed to kill process on Unix: {e}")
            return False

    def start_dashboard(self) -> bool:
        """Start the Streamlit dashboard"""
        try:
            if self.is_running():
                logger.info(f"Dashboard already running on port {self.dashboard_port}")
                return True

            # Clear any existing process on the port before starting
            logger.info(f"Checking for existing processes on port {self.dashboard_port}...")
            if self._kill_process_on_port(self.dashboard_port):
                logger.info(f"Cleared existing process on port {self.dashboard_port}")
                # Wait a moment for the port to be fully released
                time.sleep(2)

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
                logger.info("Dashboard process is not running, but checking for port conflicts...")
                # Even if our process isn't running, there might be another process on the port
                if self._kill_process_on_port(self.dashboard_port):
                    logger.info(f"Cleared conflicting process on port {self.dashboard_port}")
                    time.sleep(2)  # Wait for port to be fully released
                return True

            logger.info("Stopping Streamlit Dashboard...")

            if self.dashboard_process:
                # First try graceful termination
                self.dashboard_process.terminate()

                # Wait for graceful shutdown
                try:
                    self.dashboard_process.wait(timeout=5)
                    logger.info("Dashboard process terminated gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    logger.warning("Dashboard process didn't terminate gracefully, force killing...")
                    self.dashboard_process.kill()
                    self.dashboard_process.wait()
                    logger.info("Dashboard process force killed")

                self.dashboard_process = None

            # Additional check: make sure the port is actually free
            logger.info(f"Ensuring port {self.dashboard_port} is fully released...")
            time.sleep(1)  # Brief pause before checking
            if self._kill_process_on_port(self.dashboard_port):
                logger.info(f"Cleared remaining process on port {self.dashboard_port}")
                time.sleep(2)  # Wait for port to be fully released

            logger.info("Dashboard stopped successfully")
            return True

        except Exception as e:
            logger.exception(f"Failed to stop dashboard: {e}")
            # Even if stopping failed, try to clear the port
            try:
                self._kill_process_on_port(self.dashboard_port)
                logger.info(f"Attempted to clear port {self.dashboard_port} after error")
            except Exception as port_clear_error:
                logger.warning(f"Could not clear port after stop error: {port_clear_error}")
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
