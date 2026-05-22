"""Initialize and sync Cresus configuration."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Set, Tuple


class InitManager:
    """Manages initialization and sync of Cresus configuration.

    Syncs ~/.cresus/config/cresus.yml with init/config/cresus.yml template:
    - Preserves user values
    - Adds new keys from template
    """

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize InitManager.

        Args:
            project_root: Path to project root (defaults to finding it)
        """
        if project_root:
            self.project_root = Path(project_root)
        else:
            self.project_root = self._find_project_root()

        self.template_path = self.project_root / "init" / "config" / "cresus.yml"
        self.user_config_dir = Path.home() / ".cresus" / "config"
        self.user_config_path = self.user_config_dir / "cresus.yml"

    def _find_project_root(self) -> Path:
        """Find project root by looking for init/config/cresus.yml."""
        current = Path.cwd()

        while current != current.parent:
            if (current / "init" / "config" / "cresus.yml").exists():
                return current
            current = current.parent

        # Fallback
        return Path(__file__).resolve().parent.parent.parent

    def sync_config(self) -> Dict[str, Any]:
        """Sync user config with template.

        Reads YAML template, merges with YAML user config.

        Returns:
            Result dict with status and details
        """
        if not self.template_path.exists():
            return {
                "status": "error",
                "message": f"Template not found: {self.template_path}"
            }

        # Load template from YAML
        with open(self.template_path) as f:
            template = yaml.safe_load(f) or {}

        # Load user config from YAML (if exists)
        user_config = {}
        if self.user_config_path.exists():
            try:
                with open(self.user_config_path) as f:
                    user_config = yaml.safe_load(f) or {}
            except yaml.YAMLError:
                # If YAML is invalid, start fresh
                user_config = {}

        # Merge configs
        merged = self._merge_configs(template, user_config)

        # Save merged config as YAML
        self.user_config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.user_config_path, "w") as f:
            yaml.dump(merged, f, default_flow_style=False, sort_keys=False)

        return {
            "status": "success",
            "message": "Configuration synced successfully",
            "config_path": str(self.user_config_path),
        }

    def _merge_configs(
        self, template: Dict[str, Any], user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge template and user configs.

        Strategy:
        - Keep all user values for existing keys
        - Add new keys from template
        - Only update if key doesn't exist in user config

        Args:
            template: Template config from init/
            user: User config from ~/.cresus/

        Returns:
            Merged config dict
        """
        result = user.copy()

        # Recursively merge keys from template
        def merge_recursive(target: Dict, source: Dict, path: str = ""):
            for key, value in source.items():
                if key not in target:
                    # New key from template - add it
                    target[key] = value
                elif isinstance(value, dict) and isinstance(target.get(key), dict):
                    # Both are dicts - recurse
                    merge_recursive(target[key], value, f"{path}.{key}" if path else key)
                # else: keep user value, don't overwrite

        merge_recursive(result, template)
        return result

    def get_all_keys(self, config: Dict[str, Any]) -> Set[Tuple[str, ...]]:
        """Get all keys and nested keys as tuples.

        Returns set of key paths like:
        - ('repo',)
        - ('repo', 'path')
        - ('servers',)
        - ('servers', 'api')
        - ('servers', 'api', 'host')
        """
        keys = set()

        def traverse(obj: Any, path: Tuple[str, ...] = ()):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = path + (key,)
                    keys.add(new_path)
                    traverse(value, new_path)

        traverse(config)
        return keys

    def validate_config(self) -> Dict[str, Any]:
        """Validate user config against template.

        Returns:
            Validation result with any keys that don't exist in template
        """
        if not self.template_path.exists():
            return {
                "status": "error",
                "message": f"Template not found: {self.template_path}"
            }

        if not self.user_config_path.exists():
            return {
                "status": "ok",
                "message": "User config doesn't exist yet"
            }

        with open(self.template_path) as f:
            template = yaml.safe_load(f) or {}

        with open(self.user_config_path) as f:
            user_config = yaml.safe_load(f) or {}

        template_keys = self.get_all_keys(template)
        user_keys = self.get_all_keys(user_config)

        extra_keys = user_keys - template_keys
        missing_keys = template_keys - user_keys

        result = {
            "status": "ok" if not extra_keys else "warning",
            "template_keys_count": len(template_keys),
            "user_keys_count": len(user_keys),
        }

        if extra_keys:
            result["extra_keys"] = [".".join(k) for k in sorted(extra_keys)]

        if missing_keys:
            result["missing_keys"] = [".".join(k) for k in sorted(missing_keys)]

        return result
