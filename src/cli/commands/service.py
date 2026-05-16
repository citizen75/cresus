"""Service management commands."""

import subprocess
import os
import signal
from pathlib import Path
from typing import Optional, Dict, Any


class ServiceManager:
    """Manage API, MCP, and frontend services."""

    SERVICES = {
        "gateway": {"script": "bin/gateway", "port": 8000, "name": "Gateway (API + MCP + Cron)"},
        "front": {"script": "bin/front", "port": 5173, "name": "Frontend"},
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.pids_dir = project_root / ".pids"
        self.pids_dir.mkdir(exist_ok=True)

    def _get_pid_file(self, service: str) -> Path:
        return self.pids_dir / f"{service}.pid"

    def _save_pid(self, service: str, pid: int):
        self._get_pid_file(service).write_text(str(pid))

    def _load_pid(self, service: str) -> Optional[int]:
        pid_file = self._get_pid_file(service)
        if pid_file.exists():
            try:
                return int(pid_file.read_text().strip())
            except ValueError:
                pass
        return None

    def _get_script_interpreter(self, script: Path) -> str:
        """Detect script type and return appropriate interpreter."""
        try:
            first_line = script.read_text().split('\n')[0]
            if 'bash' in first_line or 'sh' in first_line:
                return 'bash'
        except Exception:
            pass
        return 'python'

    def start(self, service: str, daemon: bool = False) -> Dict[str, Any]:
        """Start a service."""
        if service not in self.SERVICES:
            return {"error": f"Unknown service: {service}"}

        pid = self._load_pid(service)
        if pid:
            try:
                os.kill(pid, 0)
                return {"status": "already_running", "pid": pid}
            except (OSError, ProcessLookupError):
                pass

        svc = self.SERVICES[service]
        script = self.project_root / svc["script"]
        interpreter = self._get_script_interpreter(script)
        cmd = [interpreter, str(script)]

        try:
            if daemon:
                # Disable file watcher in daemon mode (production)
                env = {**dict(os.environ.items()), "CRESUS_PROJECT_ROOT": str(self.project_root), "CRESUS_ENABLE_WATCHER": "false"}
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(self.project_root),
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                self._save_pid(service, proc.pid)
                return {"status": "started", "pid": proc.pid}
            else:
                os.execvp(interpreter, cmd)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def stop(self, service: str) -> Dict[str, Any]:
        """Stop a service."""
        if service not in self.SERVICES:
            return {"error": f"Unknown service: {service}"}

        pid = self._load_pid(service)
        if not pid:
            return {"status": "not_running"}

        try:
            os.kill(pid, signal.SIGTERM)
            self._get_pid_file(service).unlink(missing_ok=True)
            return {"status": "stopped"}
        except ProcessLookupError:
            self._get_pid_file(service).unlink(missing_ok=True)
            return {"status": "not_running"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def status(self, service: Optional[str] = None) -> Dict[str, Any]:
        """Get service status."""
        services = [service] if service else self.SERVICES.keys()
        result = {}

        for svc in services:
            if svc not in self.SERVICES:
                result[svc] = {"error": f"Unknown service: {svc}"}
                continue

            pid = self._load_pid(svc)
            if pid:
                try:
                    os.kill(pid, 0)
                    result[svc] = {"status": "running", "pid": pid}
                except (OSError, ProcessLookupError):
                    result[svc] = {"status": "stopped", "pid": pid}
            else:
                result[svc] = {"status": "stopped"}

        return result

    def logs(self, service: str, lines: int = 20) -> str:
        """Get service logs (stub)."""
        log_file = self.project_root / "logs" / f"{service}.log"
        if not log_file.exists():
            return f"No logs for {service}"

        try:
            lines_list = log_file.read_text().splitlines()
            return "\n".join(lines_list[-lines:])
        except Exception as e:
            return f"Error reading logs: {e}"

    def check_status(self, service: Optional[str] = None) -> Dict[str, Any]:
        """Check status of service(s) and display results."""
        from rich.console import Console
        from rich.table import Table

        console = Console()
        result = self.status(service)

        # Display status table
        table = Table(title="Service Status" if not service else f"Status: {service}")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("PID", style="green")

        for svc_name, svc_status in result.items():
            if "error" in svc_status:
                table.add_row(svc_name, "[red]Error[/red]", "-")
            else:
                status = svc_status.get("status", "unknown")
                status_color = "green" if status == "running" else "red"
                pid = str(svc_status.get("pid", "-"))
                table.add_row(svc_name, f"[{status_color}]{status}[/{status_color}]", pid)

        console.print(table)
        return result

    def start_services(self, service_names: str = "all", background: bool = False) -> None:
        """Start one or more services."""
        from rich.console import Console

        console = Console()

        if service_names == "all":
            services = list(self.SERVICES.keys())
        else:
            services = [service_names]

        for service in services:
            result = self.start(service, daemon=background)
            if result.get("status") == "started":
                console.print(f"[green]✓[/green] Started {service} (PID: {result['pid']})")
            elif result.get("status") == "already_running":
                console.print(f"[yellow]⚠[/yellow] {service} already running (PID: {result['pid']})")
            else:
                console.print(f"[red]✗[/red] Failed to start {service}: {result.get('message', 'Unknown error')}")

    def stop_services(self, service_names: str = "all") -> None:
        """Stop one or more services."""
        from rich.console import Console

        console = Console()

        if service_names == "all":
            services = list(self.SERVICES.keys())
        else:
            services = [service_names]

        for service in services:
            result = self.stop(service)
            if result.get("status") == "stopped":
                console.print(f"[green]✓[/green] Stopped {service}")
            elif result.get("status") == "not_running":
                console.print(f"[yellow]⚠[/yellow] {service} not running")
            else:
                console.print(f"[red]✗[/red] Failed to stop {service}: {result.get('message', 'Unknown error')}")

    def view_logs(self, service: str, follow: bool = False, lines: Optional[int] = None) -> None:
        """View service logs."""
        from rich.console import Console

        console = Console()

        if lines is None:
            lines = 20 if not follow else 50

        logs = self.logs(service, lines)
        console.print(logs)

        if follow:
            console.print("[cyan]Tailing logs (follow mode) - not implemented yet[/cyan]")
