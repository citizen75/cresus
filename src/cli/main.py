"""CLI entry point."""

import sys
import os
from pathlib import Path

# Set up project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))
os.environ.setdefault("CRESUS_PROJECT_ROOT", str(project_root))
os.chdir(project_root)

# Load environment configuration from ~/.cresus/.env
from utils.env import env


def main():
    """Start CLI."""
    from cli.app import CresusCLI

    # If arguments provided, use command mode (suppress banner)
    if len(sys.argv) > 1:
        app = CresusCLI(interactive=False)
        command = " ".join(sys.argv[1:])
        app.onecmd(command)
        return 0

    # Otherwise, enter interactive shell
    app = CresusCLI(interactive=True)
    return app.cmdloop()


if __name__ == "__main__":
    sys.exit(main())
