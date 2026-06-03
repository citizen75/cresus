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
        self.merge_report = {
            "new_files": [],
            "preserved_files": [],
            "agents_to_add": [],
            "agents_preserved": [],
            "skills_to_add": [],
            "skills_preserved": [],
            "config_files_to_add": [],
            "config_files_preserved": [],
        }

    def generate_merge_report(self):
        """Generate a detailed report of what would be merged without making changes."""
        console.print("[bold cyan]Hermes Merge Report (Dry Run)[/bold cyan]\n")
        console.print(f"[dim]Cresus template: {self.init_template}[/dim]")
        console.print(f"[dim]Hermes home: {self.hermes_home}\n[/dim]")

        if not self.init_template.exists():
            console.print(f"[red]✗ Hermes template not found: {self.init_template}[/red]")
            return False

        try:
            # Analyze config files
            self._analyze_config_files()

            # Analyze skills
            self._analyze_skills()

            # Analyze agents
            self._analyze_agents()

            # Print report
            self._print_merge_report()

            return True
        except Exception as e:
            console.print(f"[red]✗ Error generating merge report: {e}[/red]")
            return False

    def _analyze_config_files(self):
        """Analyze which config files would be added vs preserved."""
        config_src = self.init_template / "config"
        config_dst = self.hermes_home / "config"

        if not config_src.exists():
            return

        for config_file in config_src.glob("*"):
            if config_file.is_file():
                dst_file = config_dst / config_file.name
                if dst_file.exists():
                    self.merge_report["config_files_preserved"].append(config_file.name)
                else:
                    self.merge_report["config_files_to_add"].append(config_file.name)

        # Check config.yaml at root - will always be updated/backed up
        config_yaml_src = self.init_template / "config.yaml"
        config_yaml_dst = self.hermes_home / "config.yaml"

        if config_yaml_src.exists():
            if config_yaml_dst.exists():
                self.merge_report["config_files_to_add"].append("config.yaml (will backup existing to .vN)")
            else:
                self.merge_report["config_files_to_add"].append("config.yaml (new)")

    def _analyze_skills(self):
        """Analyze which skills would be added vs preserved."""
        skills_src = self.init_template / "skills"
        skills_dst = self.hermes_home / "skills"

        if not skills_src.exists():
            return

        for skill_dir in skills_src.iterdir():
            if skill_dir.is_dir():
                dst_dir = skills_dst / skill_dir.name
                if dst_dir.exists():
                    self.merge_report["skills_preserved"].append(skill_dir.name)
                else:
                    self.merge_report["skills_to_add"].append(skill_dir.name)

    def _analyze_agents(self):
        """Analyze which agents would be added vs preserved."""
        agents_src = self.init_template / "agents"
        agents_dst = self.hermes_home / "agents"

        if not agents_src.exists():
            return

        for agent_file in agents_src.glob("*.yml"):
            dst_file = agents_dst / agent_file.name
            if dst_file.exists():
                self.merge_report["agents_preserved"].append(agent_file.name)
            else:
                self.merge_report["agents_to_add"].append(agent_file.name)

    def _print_merge_report(self):
        """Print the merge report in a formatted way."""
        console.print("[bold yellow]Configuration Files[/bold yellow]")
        if self.merge_report["config_files_to_add"]:
            console.print(f"  [green]✓ Would add ({len(self.merge_report['config_files_to_add'])}):[/green]")
            for f in self.merge_report["config_files_to_add"]:
                console.print(f"    - {f}")
        if self.merge_report["config_files_preserved"]:
            console.print(f"  [cyan]⊘ Would preserve ({len(self.merge_report['config_files_preserved'])}): [/cyan]")
            for f in self.merge_report["config_files_preserved"]:
                console.print(f"    - {f}")
        if not self.merge_report["config_files_to_add"] and not self.merge_report["config_files_preserved"]:
            console.print("  [dim]No config files to analyze[/dim]")
        console.print()

        console.print("[bold yellow]Cresus Agents[/bold yellow]")
        if self.merge_report["agents_to_add"]:
            console.print(f"  [green]✓ Would add ({len(self.merge_report['agents_to_add'])}): [/green]")
            for a in self.merge_report["agents_to_add"]:
                console.print(f"    - {a}")
        if self.merge_report["agents_preserved"]:
            console.print(f"  [cyan]⊘ Would preserve ({len(self.merge_report['agents_preserved'])}): [/cyan]")
            for a in self.merge_report["agents_preserved"]:
                console.print(f"    - {a}")
        if not self.merge_report["agents_to_add"] and not self.merge_report["agents_preserved"]:
            console.print("  [dim]No agents to analyze[/dim]")
        console.print()

        console.print("[bold yellow]Cresus Skills[/bold yellow]")
        if self.merge_report["skills_to_add"]:
            console.print(f"  [green]✓ Would add ({len(self.merge_report['skills_to_add'])}): [/green]")
            for s in self.merge_report["skills_to_add"]:
                console.print(f"    - {s}")
        if self.merge_report["skills_preserved"]:
            console.print(f"  [cyan]⊘ Would preserve ({len(self.merge_report['skills_preserved'])}): [/cyan]")
            for s in self.merge_report["skills_preserved"]:
                console.print(f"    - {s}")
        if not self.merge_report["skills_to_add"] and not self.merge_report["skills_preserved"]:
            console.print("  [dim]No skills to analyze[/dim]")
        console.print()

        # Summary
        total_new = len(self.merge_report["config_files_to_add"]) + len(self.merge_report["agents_to_add"]) + len(self.merge_report["skills_to_add"])
        total_preserved = len(self.merge_report["config_files_preserved"]) + len(self.merge_report["agents_preserved"]) + len(self.merge_report["skills_preserved"])

        console.print("[bold cyan]Summary[/bold cyan]")
        console.print(f"  [green]New items to add: {total_new}[/green]")
        console.print(f"  [cyan]Existing items to preserve: {total_preserved}[/cyan]")
        console.print()

        if total_new == 0:
            console.print("[dim]Your Hermes setup is already up-to-date with Cresus templates![/dim]")
        else:
            console.print("[dim]To apply these changes, run: cresus init --hermes --merge[/dim]")

    def initialize(self, merge_only=False):
        """Initialize Hermes with Cresus configuration.

        Args:
            merge_only: If True, only copy agents and skills (not config). If False, do full init.
        """
        if merge_only:
            console.print("[bold cyan]Merging Cresus with existing Hermes setup[/bold cyan]")
        else:
            console.print("[bold cyan]Initializing Hermes Agent for Cresus[/bold cyan]")
        console.print(f"Location: {self.hermes_home}\n")

        if not self.init_template.exists():
            console.print(f"[red]✗ Hermes template not found: {self.init_template}[/red]")
            return False

        try:
            # Create directory structure
            self._create_directories()

            # Copy configuration files (skip if merge_only)
            if not merge_only:
                self._copy_config_files()

            # Setup config.yaml with versioned backups (not skipped in merge_only)
            self._setup_config_yaml()

            # Copy skills
            self._copy_skills()

            # Copy agents
            self._copy_agents()

            # Setup environment (skip if merge_only)
            if not merge_only:
                self._setup_environment()

            console.print(f"\n[bold green]✓ Hermes {'merged' if merge_only else 'initialized'} successfully![/bold green]")
            console.print(f"[dim]Location: {self.hermes_home}[/dim]")

            if not merge_only:
                console.print(f"[dim]Edit {self.hermes_home / 'config' / 'hermes.yml'} to customize settings[/dim]")
                console.print(f"\n[bold cyan]Next steps:[/bold cyan]")
                console.print("[dim]1. Edit ~/.hermes/config/hermes.yml to set API URL and other settings[/dim]")
                console.print("[dim]2. Start the Cresus API: cresus service start api[/dim]")
                console.print("[dim]3. Launch Hermes with: hermes run[/dim]")

            return True

        except Exception as e:
            console.print(f"[red]✗ Error {'merging' if merge_only else 'initializing'} Hermes: {e}[/red]")
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

        # Copy individual config files
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

        # Copy skill directories (each skill is a folder)
        for skill_dir in skills_src.iterdir():
            if skill_dir.is_dir():
                dst_dir = skills_dst / skill_dir.name
                if not dst_dir.exists():
                    try:
                        import shutil
                        shutil.copytree(skill_dir, dst_dir)
                        copied.append(skill_dir.name)
                    except Exception as e:
                        console.print(f"[red]✗ Error copying {skill_dir.name}: {e}[/red]")
                else:
                    # Skill directory already exists - don't overwrite
                    skipped.append(skill_dir.name)

        if copied:
            console.print(f"[green]✓ Copied {len(copied)} skill(s): {', '.join(copied)}[/green]")

        if skipped:
            console.print(f"[dim]⊘ Preserved {len(skipped)} existing skill(s): {', '.join(skipped)}[/dim]")

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

    def _backup_with_versioning(self, file_path: Path) -> bool:
        """Backup existing file with version numbering.

        Args:
            file_path: Path to the file to backup

        Returns:
            True if backup was created or file doesn't exist, False on error
        """
        if not file_path.exists():
            return True

        try:
            # Find the next available version number
            version = 1
            while True:
                backup_path = file_path.parent / f"{file_path.name}.v{version}"
                if not backup_path.exists():
                    break
                version += 1

            # Create backup
            with open(file_path, "r") as f:
                content = f.read()
            with open(backup_path, "w") as f:
                f.write(content)

            console.print(f"[cyan]✓ Backed up existing {file_path.name} → {file_path.name}.v{version}[/cyan]")
            return True

        except Exception as e:
            console.print(f"[red]✗ Error backing up {file_path.name}: {e}[/red]")
            return False

    def _setup_config_yaml(self):
        """Setup config.yaml with versioned backups."""
        config_yaml_src = self.init_template / "config.yaml"
        config_yaml_dst = self.hermes_home / "config.yaml"

        if not config_yaml_src.exists():
            console.print("[yellow]⚠ config.yaml template not found[/yellow]")
            return

        try:
            # Backup existing config.yaml if it exists
            if config_yaml_dst.exists():
                if not self._backup_with_versioning(config_yaml_dst):
                    return

            # Copy new config.yaml
            with open(config_yaml_src, "r") as f:
                content = f.read()
            with open(config_yaml_dst, "w") as f:
                f.write(content)

            console.print("[green]✓ Created config.yaml[/green]")

        except Exception as e:
            console.print(f"[red]✗ Error setting up config.yaml: {e}[/red]")

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
