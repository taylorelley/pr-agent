"""
Configuration merger module for path-based configuration merging.

This module implements Task 2.2 from Feature 2: Path-Based Merge Rules
"""

from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional
import tomllib
import copy

from jinja2.exceptions import SecurityError
from pr_agent.log import get_logger
from pr_agent.custom_merge_loader import validate_file_security
from pr_agent.path_config.config_discovery import ConfigFile


class MergeStrategy(Enum):
    """
    Defines how configuration values should be merged.

    OVERRIDE: Child completely replaces parent value
    EXTEND: Child adds to parent list/dict
    INHERIT: Child inherits parent if not specified
    """
    OVERRIDE = "override"
    EXTEND = "extend"
    INHERIT = "inherit"


class ConfigMerger:
    """
    Merges multiple configuration files with path-based precedence rules.

    This class implements depth-aware configuration merging where:
    1. Deeper configs take precedence over shallower ones
    2. Merge strategies can be specified per-section
    3. Security validation is enforced on all configs
    """

    # Settings that are allowed to be overridden at subdirectory level
    DEFAULT_ALLOWED_OVERRIDES: ClassVar[List[str]] = [
        "pr_reviewer.extra_instructions",
        "pr_reviewer.num_max_findings",
        "pr_reviewer.require_score_review",
        "pr_reviewer.require_tests_review",
        "pr_reviewer.require_security_review",
        "pr_code_suggestions.extra_instructions",
        "pr_code_suggestions.num_code_suggestions",
        "pr_description.extra_instructions",
        "pr_questions.extra_instructions",
    ]

    # Settings that should NEVER be overridden at subdirectory level (security)
    DENIED_OVERRIDES: ClassVar[List[str]] = [
        "config.model",
        "config.fallback_models",
        "openai.key",
        "openai.api_key",
        "anthropic.key",
        "config.git_provider",
        "github.user_token",
        "gitlab.personal_access_token",
        "bitbucket.bearer_token",
    ]

    def __init__(
        self,
        repo_root: Path,
        max_depth: int = 5,
        allowed_overrides: Optional[List[str]] = None,
        denied_overrides: Optional[List[str]] = None
    ):
        """
        Initialize the configuration merger.

        Args:
            repo_root: Root directory of the repository
            max_depth: Maximum depth to enforce (security limit)
            allowed_overrides: List of setting paths allowed to be overridden (None = use defaults)
            denied_overrides: List of setting paths denied from override (None = use defaults)
        """
        self.repo_root = Path(repo_root).resolve()
        self.max_depth = max_depth
        self.allowed_overrides = allowed_overrides or self.DEFAULT_ALLOWED_OVERRIDES
        self.denied_overrides = denied_overrides or self.DENIED_OVERRIDES
        self.logger = get_logger()

    def merge_configs(
        self,
        config_files: List[ConfigFile],
        base_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Merge multiple configuration files with depth-aware precedence.

        Configs are merged in order from root to leaf (shallowest to deepest).
        Deeper configs take precedence based on merge strategy.

        Args:
            config_files: List of ConfigFile objects sorted by depth
            base_config: Optional base configuration to start with

        Returns:
            Merged configuration dictionary
        """
        merged = copy.deepcopy(base_config) if base_config else {}

        self.logger.debug(
            f"Merging {len(config_files)} configuration files",
            extra={"config_count": len(config_files)}
        )

        for config_file in config_files:
            try:
                # Load the config file
                config_data = self._load_config_file(config_file)

                # Validate security
                validate_file_security(config_data, str(config_file.path))

                # Validate overrides if not root config
                if config_file.depth > 0:
                    self._validate_overrides(config_data, config_file)

                # Merge into accumulated config
                merged = self._merge_dict(
                    merged,
                    config_data,
                    config_file,
                    is_root=(config_file.depth == 0)
                )

                self.logger.info(
                    f"Merged config from {config_file.relative_path}",
                    extra={
                        "config_path": str(config_file.relative_path),
                        "depth": config_file.depth
                    }
                )

            except Exception as e:
                self.logger.exception(
                    f"Failed to merge config from {config_file.path}",
                    extra={"config_path": str(config_file.path)}
                )
                # Continue with other configs rather than failing completely
                continue

        return merged

    def _load_config_file(self, config_file: ConfigFile) -> Dict[str, Any]:
        """
        Load a TOML configuration file.

        Args:
            config_file: ConfigFile object to load

        Returns:
            Parsed configuration dictionary
        """
        with open(config_file.path, 'rb') as f:
            return tomllib.load(f)

    def _validate_overrides(self, config_data: Dict[str, Any], config_file: ConfigFile) -> None:
        """
        Validate that subdirectory configs only override allowed settings.

        Args:
            config_data: Configuration data to validate
            config_file: Source ConfigFile for error messages

        Raises:
            SecurityError: If forbidden overrides are detected
        """
        # Flatten the config to check all paths
        flat_config = self._flatten_dict(config_data)

        for key_path, _value in flat_config.items():
            # Check if this is a denied override
            if any(key_path.startswith(denied) for denied in self.denied_overrides):
                raise SecurityError(
                    f"Security error in {config_file.path}: "
                    f"Setting '{key_path}' cannot be overridden in subdirectory configs. "
                    f"This setting must be defined at the repository root level only."
                )

            # Check if this is an allowed override
            is_allowed = any(
                key_path.startswith(allowed) or key_path == allowed
                for allowed in self.allowed_overrides
            )

            if not is_allowed:
                self.logger.warning(
                    f"Config override not in allowed list: {key_path}",
                    extra={
                        "config_path": str(config_file.relative_path),
                        "setting": key_path,
                        "depth": config_file.depth
                    }
                )

    def _merge_dict(
        self,
        base: Dict[str, Any],
        overlay: Dict[str, Any],
        config_file: ConfigFile,
        is_root: bool = False,
        parent_key: str = ""
    ) -> Dict[str, Any]:
        """
        Recursively merge two configuration dictionaries.

        Args:
            base: Base configuration dictionary
            overlay: Overlay configuration to merge
            config_file: Source ConfigFile for logging
            is_root: Whether this is the root config
            parent_key: Parent key path for nested merging

        Returns:
            Merged configuration dictionary
        """
        result = copy.deepcopy(base)

        for key, value in overlay.items():
            full_key = f"{parent_key}.{key}" if parent_key else key

            # Check for merge strategy directive
            merge_strategy = self._get_merge_strategy(overlay, key, is_root)

            if key not in result:
                # Key doesn't exist in base, just add it
                result[key] = copy.deepcopy(value)
            elif isinstance(value, dict) and isinstance(result[key], dict):
                # Both are dicts, merge recursively
                if merge_strategy == MergeStrategy.OVERRIDE:
                    result[key] = copy.deepcopy(value)
                elif merge_strategy == MergeStrategy.EXTEND:
                    result[key] = self._merge_dict(
                        result[key],
                        value,
                        config_file,
                        is_root=False,
                        parent_key=full_key
                    )
                else:  # INHERIT or default
                    result[key] = self._merge_dict(
                        result[key],
                        value,
                        config_file,
                        is_root=False,
                        parent_key=full_key
                    )
            elif isinstance(value, list) and isinstance(result[key], list):
                # Both are lists, merge based on strategy
                if merge_strategy == MergeStrategy.EXTEND:
                    result[key] = result[key] + value
                else:  # OVERRIDE or INHERIT
                    result[key] = copy.deepcopy(value)
            else:
                # Different types or scalar values - overlay wins
                result[key] = copy.deepcopy(value)

        return result

    def _get_merge_strategy(
        self,
        config_section: Dict[str, Any],
        key: str,
        is_root: bool
    ) -> MergeStrategy:
        """
        Determine the merge strategy for a configuration section.

        Looks for _merge_strategy directive in the section.

        Args:
            config_section: Configuration section dictionary
            key: Key being merged
            is_root: Whether this is root config

        Returns:
            MergeStrategy to use
        """
        # Root configs always use EXTEND strategy
        if is_root:
            return MergeStrategy.EXTEND

        # Look for _merge_strategy directive in the section
        if isinstance(config_section.get(key), dict):
            strategy_value = config_section[key].get('_merge_strategy')
            if strategy_value:
                try:
                    return MergeStrategy(strategy_value)
                except ValueError:
                    self.logger.warning(
                        f"Invalid merge strategy '{strategy_value}', using default",
                        extra={"strategy": strategy_value, "key": key}
                    )

        # Default strategy for non-root configs
        return MergeStrategy.OVERRIDE

    def _flatten_dict(
        self,
        d: Dict[str, Any],
        parent_key: str = "",
        sep: str = "."
    ) -> Dict[str, Any]:
        """
        Flatten a nested dictionary to dot-notation paths.

        Args:
            d: Dictionary to flatten
            parent_key: Parent key path
            sep: Separator for key paths

        Returns:
            Flattened dictionary with dot-notation keys
        """
        items = []
        for key, value in d.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key

            # Skip merge strategy directives
            if key == '_merge_strategy':
                continue

            if isinstance(value, dict):
                items.extend(self._flatten_dict(value, new_key, sep=sep).items())
            else:
                items.append((new_key, value))

        return dict(items)

    def validate_config_consistency(
        self,
        config_files: List[ConfigFile]
    ) -> List[Dict[str, Any]]:
        """
        Validate configuration files for conflicts and issues.

        Args:
            config_files: List of ConfigFile objects to validate

        Returns:
            List of validation issues found
        """
        issues = []

        for config_file in config_files:
            try:
                config_data = self._load_config_file(config_file)

                # Validate security
                validate_file_security(config_data, str(config_file.path))

                # Validate overrides for non-root configs
                if config_file.depth > 0:
                    try:
                        self._validate_overrides(config_data, config_file)
                    except Exception as e:
                        issues.append({
                            "file": str(config_file.relative_path),
                            "type": "security_violation",
                            "message": str(e)
                        })

            except Exception as e:
                issues.append({
                    "file": str(config_file.relative_path),
                    "type": "load_error",
                    "message": str(e)
                })

        return issues
