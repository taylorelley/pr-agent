"""
Configuration resolver module for getting effective configuration for specific files.

This module implements Task 2.4 from Feature 2: Per-File Configuration Resolution
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from pr_agent.log import get_logger
from pr_agent.config_loader import get_settings
from pr_agent.path_config.config_discovery import ConfigDiscovery, ConfigFile
from pr_agent.path_config.config_merger import ConfigMerger


@dataclass
class ResolvedConfig:
    """
    Represents a resolved configuration for a specific file.

    Attributes:
        config: The effective configuration dictionary
        source_configs: List of config files that contributed to this resolution
        file_path: The file this config was resolved for
    """
    config: Dict[str, Any]
    source_configs: List[ConfigFile]
    file_path: str

    def get_applied_config_info(self) -> str:
        """
        Get a human-readable description of which configs were applied.

        Returns:
            String describing the config sources
        """
        if not self.source_configs:
            return "Using global configuration only"

        sources = [str(cfg.relative_path) for cfg in self.source_configs]
        return f"Applied configs: {' → '.join(sources)}"


class ConfigResolver:
    """
    Resolves effective configuration for specific files in a PR.

    This class orchestrates ConfigDiscovery and ConfigMerger to provide
    the final effective configuration for any given file path.
    """

    def __init__(
        self,
        repo_root: Path,
        max_depth: int = 5,
        enable_path_config: bool = True
    ):
        """
        Initialize the configuration resolver.

        Args:
            repo_root: Root directory of the repository
            max_depth: Maximum depth for config search
            enable_path_config: Whether path-based config is enabled
        """
        self.repo_root = Path(repo_root).resolve()
        self.max_depth = max_depth
        self.enable_path_config = enable_path_config
        self.logger = get_logger()

        # Initialize discovery and merger
        self.discovery = ConfigDiscovery(repo_root, max_depth)
        self.merger = ConfigMerger(repo_root, max_depth)

        # Cache for resolved configs per file
        self._resolution_cache: Dict[str, ResolvedConfig] = {}

    def get_config_for_file(
        self,
        file_path: str,
        changed_files: Optional[List[str]] = None
    ) -> ResolvedConfig:
        """
        Get the effective configuration for a specific file.

        This method:
        1. Discovers all relevant config files
        2. Filters to those that apply to the given file
        3. Merges them with proper precedence
        4. Returns the effective configuration

        Args:
            file_path: Path to the file (relative to repo root)
            changed_files: Optional list of all changed files (for caching)

        Returns:
            ResolvedConfig with effective configuration and metadata
        """
        # Check cache
        if file_path in self._resolution_cache:
            self.logger.debug(f"Using cached config resolution for {file_path}")
            return self._resolution_cache[file_path]

        # If path-based config is disabled, return global config only
        if not self.enable_path_config:
            return ResolvedConfig(
                config={},  # Empty - will use global settings
                source_configs=[],
                file_path=file_path
            )

        # Discover configs
        files_to_check = changed_files or [file_path]
        all_configs = self.discovery.discover_configs(files_to_check)

        # Filter configs that apply to this specific file
        applicable_configs = self._filter_applicable_configs(file_path, all_configs)

        # Merge the applicable configs
        merged_config = self.merger.merge_configs(applicable_configs)

        # Create resolved config
        resolved = ResolvedConfig(
            config=merged_config,
            source_configs=applicable_configs,
            file_path=file_path
        )

        # Cache the result
        self._resolution_cache[file_path] = resolved

        self.logger.info(
            f"Resolved config for {file_path}",
            extra={
                "file_path": file_path,
                "config_count": len(applicable_configs),
                "sources": [str(c.relative_path) for c in applicable_configs]
            }
        )

        return resolved

    def get_config_for_files(
        self,
        file_paths: List[str]
    ) -> Dict[str, ResolvedConfig]:
        """
        Get effective configuration for multiple files efficiently.

        This method discovers configs once and reuses them for all files.

        Args:
            file_paths: List of file paths (relative to repo root)

        Returns:
            Dictionary mapping file paths to ResolvedConfig objects
        """
        if not self.enable_path_config or not file_paths:
            return {
                path: ResolvedConfig(config={}, source_configs=[], file_path=path)
                for path in file_paths
            }

        # Discover all configs once
        all_configs = self.discovery.discover_configs(file_paths)

        # Resolve for each file
        results = {}
        for file_path in file_paths:
            # Check cache first
            if file_path in self._resolution_cache:
                results[file_path] = self._resolution_cache[file_path]
                continue

            # Filter and merge
            applicable_configs = self._filter_applicable_configs(file_path, all_configs)
            merged_config = self.merger.merge_configs(applicable_configs)

            resolved = ResolvedConfig(
                config=merged_config,
                source_configs=applicable_configs,
                file_path=file_path
            )

            self._resolution_cache[file_path] = resolved
            results[file_path] = resolved

        return results

    def _filter_applicable_configs(
        self,
        file_path: str,
        all_configs: List[ConfigFile]
    ) -> List[ConfigFile]:
        """
        Filter config files to those that apply to the given file path.

        A config applies to a file if the file is in the same directory
        or a subdirectory of the config file.

        Args:
            file_path: File path relative to repo root
            all_configs: All discovered config files

        Returns:
            List of applicable ConfigFile objects
        """
        file_abs_path = self.repo_root / file_path
        applicable = []

        for config in all_configs:
            config_dir = config.path.parent

            # Check if file is in this config's directory or subdirectory
            try:
                file_abs_path.relative_to(config_dir)
                applicable.append(config)
            except ValueError:
                # File is not in this config's directory tree
                continue

        return applicable

    def get_effective_setting(
        self,
        file_path: str,
        setting_path: str,
        default: Any = None
    ) -> Any:
        """
        Get a specific setting value for a file, with path-based override.

        This method:
        1. Gets the resolved config for the file
        2. Looks up the setting in that config
        3. Falls back to global settings if not found

        Args:
            file_path: File path relative to repo root
            setting_path: Dot-notation path to setting (e.g., "pr_reviewer.extra_instructions")
            default: Default value if setting not found

        Returns:
            The setting value, or default if not found
        """
        # Get resolved config
        resolved = self.get_config_for_file(file_path)

        # Try to get from resolved config first (using lowercase)
        parts = setting_path.lower().split('.')
        current = resolved.config

        try:
            for part in parts:
                current = current[part]
        except (KeyError, TypeError):
            pass
        else:
            return current

        # Fall back to global settings (also using lowercase for consistency)
        global_value = get_settings().get(setting_path.lower())
        if global_value is not None:
            return global_value

        return default

    def validate_all_configs(
        self,
        changed_files: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Validate all discovered configurations for consistency and security.

        Args:
            changed_files: List of changed files to discover configs for

        Returns:
            List of validation issues (empty list if all valid)
        """
        # Discover all configs
        all_configs = self.discovery.discover_configs(changed_files)

        # Validate using merger
        issues = self.merger.validate_config_consistency(all_configs)

        if issues:
            self.logger.warning(
                f"Found {len(issues)} configuration validation issues",
                extra={"issue_count": len(issues)}
            )
        else:
            self.logger.info("All configurations validated successfully")

        return issues

    def get_config_summary(
        self,
        changed_files: List[str]
    ) -> Dict[str, Any]:
        """
        Get a summary of the configuration state for changed files.

        Args:
            changed_files: List of changed files

        Returns:
            Dictionary with configuration summary information
        """
        all_configs = self.discovery.discover_configs(changed_files)

        summary = {
            "path_config_enabled": self.enable_path_config,
            "repo_root": str(self.repo_root),
            "max_depth": self.max_depth,
            "discovered_configs": [
                {
                    "path": str(cfg.relative_path),
                    "depth": cfg.depth
                }
                for cfg in all_configs
            ],
            "changed_files_count": len(changed_files),
            "cache_size": self.discovery.get_cache_size()
        }

        return summary

    def clear_cache(self) -> None:
        """Clear all caches. Useful for testing or long-running processes."""
        self._resolution_cache.clear()
        self.discovery.clear_cache()
        self.logger.debug("Cleared all configuration caches")
