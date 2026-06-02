"""Hermes initialization command for Cresus CLI."""

import os
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


class HermesInitializer:
    """Initialize Hermes agent configuration for Cresus."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.hermes_home = Path.home() / ".hermes"
        self.init_template = project_root / "init" / "hermes"

    def initialize(self):
        """Initialize Hermes with Cresus configuration."""
        console.print("[bold cyan]Initializing Hermes Agent for Cresus[/bold cyan]")
        console.print(f"Location: {self.hermes_home}\n")

        if not self.init_template.exists():
            console.print(f"[red]✗ Hermes template not found: {self.init_template}[/red]")
            return False

        try:
            # Create directory structure
            self._create_directories()

            # Copy configuration files
            self._copy_config_files()

            # Copy skills
            self._copy_skills()

            # Copy agents
            self._copy_agents()

            # Setup environment
            self._setup_environment()

            console.print(f"\n[bold green]✓ Hermes initialized successfully![/bold green]")
            console.print(f"[dim]Configuration location: {self.hermes_home}[/dim]")
            console.print(f"[dim]Edit {self.hermes_home / 'config' / 'hermes.yml'} to customize settings[/dim]")
            console.print(f"\n[bold cyan]Next steps:[/bold cyan]")
            console.print("[dim]1. Edit ~/.hermes/config/hermes.yml to set API URL and other settings[/dim]")
            console.print("[dim]2. Start the Cresus API: cresus service start api[/dim]")
            console.print("[dim]3. Launch Hermes with: hermes run[/dim]")

            return True

        except Exception as e:
            console.print(f"[red]✗ Error initializing Hermes: {e}[/red]")
            return False

    def _create_directories(self):
        """Create required directory structure."""
        dirs = [
            self.hermes_home,
            self.hermes_home / "config",
            self.hermes_home / "skills",
            self.hermes_home / "agents",
            self.hermes_home / "logs",
            self.hermes_home / "data",
            self.hermes_home / "cache",
        ]

        created = []
        for d in dirs:
            if not d.exists():
                d.mkdir(parents=True, exist_ok=True)
                created.append(d)

        if created:
            console.print(f"[green]✓ Created {len(created)} directories[/green]")

    def _copy_config_files(self):
        """Copy configuration files from template (skip if they exist)."""
        config_src = self.init_template / "config"
        config_dst = self.hermes_home / "config"

        if not config_src.exists():
            console.print("[yellow]⚠ Config template not found[/yellow]")
            return

        copied = []
        skipped = []

        for config_file in config_src.glob("*"):
            if config_file.is_file():
                dst_file = config_dst / config_file.name
                if not dst_file.exists():
                    try:
                        with open(config_file, "r") as f:
                            content = f.read()
                        with open(dst_file, "w") as f:
                            f.write(content)
                        copied.append(config_file.name)
                    except Exception as e:
                        console.print(f"[red]✗ Error copying {config_file.name}: {e}[/red]")
                else:
                    # File already exists - don't overwrite
                    skipped.append(config_file.name)

        if copied:
            console.print(f"[green]✓ Copied {len(copied)} config file(s)[/green]")

        if skipped:
            console.print(f"[dim]⊘ Preserved {len(skipped)} existing config file(s): {', '.join(skipped)}[/dim]")

    def _copy_skills(self):
        """Copy skill definitions from template (skip if they exist)."""
        skills_src = self.init_template / "skills"
        skills_dst = self.hermes_home / "skills"

        if not skills_src.exists():
            console.print("[yellow]⚠ Skills template not found[/yellow]")
            return

        copied = []
        skipped = []

        for skill_file in skills_src.glob("*.yml"):
            dst_file = skills_dst / skill_file.name
            if not dst_file.exists():
                try:
                    with open(skill_file, "r") as f:
                        content = f.read()
                    with open(dst_file, "w") as f:
                        f.write(content)
                    copied.append(skill_file.name)
                except Exception as e:
                    console.print(f"[red]✗ Error copying {skill_file.name}: {e}[/red]")
            else:
                # Skill already exists - don't overwrite
                skipped.append(skill_file.name)

        if copied:
            console.print(f"[green]✓ Copied {len(copied)} skill(s): {', '.join([f.replace('.yml', '') for f in copied])}[/green]")

        if skipped:
            console.print(f"[dim]⊘ Preserved {len(skipped)} existing skill(s): {', '.join([f.replace('.yml', '') for f in skipped])}[/dim]")

    def _copy_agents(self):
        """Copy agent definitions from template (skip if they exist)."""
        agents_src = self.init_template / "agents"
        agents_dst = self.hermes_home / "agents"

        if not agents_src.exists():
            console.print("[yellow]⚠ Agents template not found[/yellow]")
            return

        copied = []
        skipped = []

        for agent_file in agents_src.glob("*.yml"):
            dst_file = agents_dst / agent_file.name
            if not dst_file.exists():
                try:
                    with open(agent_file, "r") as f:
                        content = f.read()
                    with open(dst_file, "w") as f:
                        f.write(content)
                    copied.append(agent_file.name)
                except Exception as e:
                    console.print(f"[red]✗ Error copying {agent_file.name}: {e}[/red]")
            else:
                # Agent already exists - don't overwrite
                skipped.append(agent_file.name)

        if copied:
            console.print(f"[green]✓ Copied {len(copied)} agent(s)[/green]")

        if skipped:
            console.print(f"[dim]⊘ Preserved {len(skipped)} existing agent(s): {', '.join(skipped)}[/dim]")

    def _setup_environment(self):
        """Setup Hermes environment configuration (skip if it exists)."""
        env_file = self.hermes_home / ".env"

        if not env_file.exists():
            env_content = """# Hermes Environment Configuration
# Auto-generated by: cresus init --hermes

# API Configuration
CRESUS_API_URL=http://localhost:8000/api/v1
CRESUS_API_KEY=

# Hermes Configuration
HERMES_HOME=~/.hermes
HERMES_LOG_LEVEL=INFO
HERMES_LOG_FILE=~/.hermes/logs/hermes.log

# MCP Server Configuration
MCP_SERVER=stdio
MCP_TIMEOUT=30
MCP_RETRIES=3

# Model Configuration
HERMES_MODEL=gpt-4
HERMES_TEMPERATURE=0.7
HERMES_MAX_TOKENS=2000

# Safety Settings
HERMES_REQUIRE_CONFIRMATION=true
HERMES_MAX_PORTFOLIO_SIZE=50
HERMES_DAILY_LOSS_LIMIT=-0.05

# Features
HERMES_ENABLE_PROACTIVE_ALERTS=true
HERMES_ENABLE_LEARNING=true
HERMES_TRACK_PERFORMANCE=true
"""

            try:
                with open(env_file, "w") as f:
                    f.write(env_content)
                console.print("[green]✓ Created .env configuration[/green]")
            except Exception as e:
                console.print(f"[red]✗ Error creating .env: {e}[/red]")
        else:
            console.print("[dim]⊘ .env already exists (using existing configuration)[/dim]")
