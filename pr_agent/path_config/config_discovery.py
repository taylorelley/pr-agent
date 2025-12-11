"""
Configuration discovery module for finding .pr_agent.toml files in a repository.

This module implements Task 2.1 from Feature 2: Configuration Discovery
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set
import hashlib

from pr_agent.log import get_logger


# Supported configuration file names (in order of precedence)
CONFIG_FILENAMES = [
    '.pr_agent.toml',
    'pr_agent.toml',
    '.pr-agent.toml',
]


@dataclass(frozen=True)
class ConfigFile:
    """
    Represents a discovered configuration file with its metadata.

    Frozen for immutability since it's used in sets and as cache keys.
    """
    path: Path
    depth: int  # Depth from repository root (0 = root)
    relative_path: Path  # Relative to repository root


class ConfigDiscovery:
    """
    Discovers and caches .pr_agent.toml configuration files in a repository.

    This class implements path-based configuration discovery by:
    1. Walking the directory tree from changed file locations upward
    2. Caching discovered configs per PR to avoid repeated filesystem access
    3. Supporting multiple config file name variations
    4. Enforcing maximum depth limits for security
    """

    def __init__(self, repo_root: Path, max_depth: int = 5):
        """
        Initialize the configuration discovery system.

        Args:
            repo_root: Root directory of the repository
            max_depth: Maximum depth to search for config files (security limit)
        """
        self.repo_root = Path(repo_root).resolve()
        self.max_depth = max_depth
        self._cache: dict[str, List[ConfigFile]] = {}
        self.logger = get_logger()

    def discover_configs(self, changed_files: List[str]) -> List[ConfigFile]:
        """
        Discover all relevant .pr_agent.toml files for the given changed files.

        This method:
        1. Finds all config files in the directory hierarchy
        2. Caches results for performance
        3. Returns configs sorted by depth (root first)

        Args:
            changed_files: List of file paths relative to repository root

        Returns:
            List of ConfigFile objects sorted by depth (root first)
        """
        # Generate cache key based on changed files
        cache_key = self._generate_cache_key(changed_files)

        # Check cache first
        if cache_key in self._cache:
            self.logger.debug(f"Using cached config discovery for {len(changed_files)} files")
            return self._cache[cache_key]

        # Discover configs
        configs = self._discover_configs_uncached(changed_files)

        # Cache the result
        self._cache[cache_key] = configs

        self.logger.info(
            f"Discovered {len(configs)} configuration files",
            extra={"config_count": len(configs), "changed_files_count": len(changed_files)}
        )

        return configs

    def _discover_configs_uncached(self, changed_files: List[str]) -> List[ConfigFile]:
        """
        Perform actual config discovery without caching.

        Args:
            changed_files: List of file paths relative to repository root

        Returns:
            List of ConfigFile objects sorted by depth (root first)
        """
        discovered_configs: Set[ConfigFile] = set()

        # Always check for root config
        root_config = self._find_config_at_path(self.repo_root)
        if root_config:
            discovered_configs.add(root_config)

        # Check each changed file's directory hierarchy
        for file_path in changed_files:
            file_abs_path = self.repo_root / file_path
            configs = self._walk_up_from_file(file_abs_path)
            discovered_configs.update(configs)

        # Sort by depth (root first)
        sorted_configs = sorted(discovered_configs, key=lambda c: c.depth)

        return sorted_configs

    def _walk_up_from_file(self, file_path: Path) -> List[ConfigFile]:
        """
        Walk up the directory tree from a file location, finding all config files.

        Args:
            file_path: Absolute path to the changed file

        Returns:
            List of discovered ConfigFile objects
        """
        configs: List[ConfigFile] = []

        # Start from the file's parent directory
        # For non-existent files (e.g., new files in PR), is_file() returns False,
        # so we correctly use the parent of the intended file path
        current_dir = file_path.parent if file_path.is_file() else file_path

        # Walk up the tree
        depth = 0
        while True:
            # Security: Enforce max depth limit
            if depth > self.max_depth:
                self.logger.warning(
                    f"Maximum config search depth ({self.max_depth}) reached",
                    extra={"file_path": str(file_path), "max_depth": self.max_depth}
                )
                break

            # Check if we've reached the repository root
            if not self._is_within_repo(current_dir):
                break

            # Look for config file at this level
            config = self._find_config_at_path(current_dir)
            if config:
                configs.append(config)

            # Stop if we've reached the repo root
            if current_dir == self.repo_root:
                break

            # Move up one directory
            parent = current_dir.parent
            if parent == current_dir:  # Reached filesystem root
                break

            current_dir = parent
            depth += 1

        return configs

    def _find_config_at_path(self, directory: Path) -> Optional[ConfigFile]:
        """
        Find a config file in the specified directory.

        Checks for config files in order of precedence defined in CONFIG_FILENAMES.

        Args:
            directory: Directory to search in

        Returns:
            ConfigFile if found, None otherwise
        """
        for config_name in CONFIG_FILENAMES:
            config_path = directory / config_name
            if config_path.is_file():
                try:
                    relative_path = config_path.relative_to(self.repo_root)
                    depth = len(relative_path.parent.parts)

                    return ConfigFile(
                        path=config_path,
                        depth=depth,
                        relative_path=relative_path
                    )
                except ValueError:
                    # Path is not relative to repo_root
                    self.logger.warning(
                        f"Config file found outside repository: {config_path}",
                        extra={"config_path": str(config_path), "repo_root": str(self.repo_root)}
                    )
                    continue

        return None

    def _is_within_repo(self, path: Path) -> bool:
        """
        Check if a path is within the repository root.

        Args:
            path: Path to check

        Returns:
            True if path is within repo, False otherwise
        """
        try:
            path.relative_to(self.repo_root)
            return True
        except ValueError:
            return False

    def _generate_cache_key(self, changed_files: List[str]) -> str:
        """
        Generate a cache key for a set of changed files.

        Args:
            changed_files: List of file paths

        Returns:
            Hash-based cache key
        """
        # Sort files for consistent hashing
        sorted_files = sorted(changed_files)
        content = '|'.join(sorted_files)
        return hashlib.md5(content.encode()).hexdigest()

    def clear_cache(self) -> None:
        """Clear the discovery cache. Useful for testing or long-running processes."""
        self._cache.clear()
        self.logger.debug("Cleared config discovery cache")

    def get_cache_size(self) -> int:
        """
        Get the number of cached discovery results.

        Returns:
            Number of cached entries
        """
        return len(self._cache)
