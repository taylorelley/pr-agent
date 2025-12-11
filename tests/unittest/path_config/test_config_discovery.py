"""
Unit tests for ConfigDiscovery class.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from pr_agent.path_config.config_discovery import ConfigDiscovery, ConfigFile, CONFIG_FILENAMES


class TestConfigDiscovery:
    """Test suite for ConfigDiscovery class."""

    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository structure for testing."""
        temp_dir = tempfile.mkdtemp()
        repo_root = Path(temp_dir)

        # Create directory structure
        (repo_root / "src").mkdir()
        (repo_root / "src" / "backend").mkdir()
        (repo_root / "src" / "frontend").mkdir()
        (repo_root / "tests").mkdir()

        # Create some files
        (repo_root / "src" / "backend" / "main.py").touch()
        (repo_root / "src" / "frontend" / "app.tsx").touch()
        (repo_root / "tests" / "test_main.py").touch()

        yield repo_root

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def discovery(self, temp_repo):
        """Create a ConfigDiscovery instance."""
        return ConfigDiscovery(temp_repo, max_depth=5)

    def test_init(self, temp_repo):
        """Test ConfigDiscovery initialization."""
        discovery = ConfigDiscovery(temp_repo, max_depth=3)
        assert discovery.repo_root == temp_repo.resolve()
        assert discovery.max_depth == 3
        assert len(discovery._cache) == 0

    def test_find_root_config(self, temp_repo, discovery):
        """Test finding configuration at repository root."""
        # Create root config
        config_path = temp_repo / ".pr_agent.toml"
        config_path.write_text("[config]\nmodel = 'gpt-4'")

        configs = discovery.discover_configs(["src/backend/main.py"])

        assert len(configs) == 1
        assert configs[0].path == config_path
        assert configs[0].depth == 0

    def test_find_nested_configs(self, temp_repo, discovery):
        """Test finding multiple nested configuration files."""
        # Create configs at different levels
        (temp_repo / ".pr_agent.toml").write_text("[config]\nmodel = 'gpt-4'")
        (temp_repo / "src" / ".pr_agent.toml").write_text("[pr_reviewer]\nextra_instructions = 'src level'")
        (temp_repo / "src" / "backend" / ".pr_agent.toml").write_text(
            "[pr_reviewer]\nextra_instructions = 'backend level'"
        )

        configs = discovery.discover_configs(["src/backend/main.py"])

        assert len(configs) == 3
        # Should be sorted by depth (root first)
        assert configs[0].depth == 0
        assert configs[1].depth == 1
        assert configs[2].depth == 2

    def test_alternative_config_names(self, temp_repo, discovery):
        """Test support for alternative config file names."""
        # Test each supported name
        for config_name in CONFIG_FILENAMES:
            config_path = temp_repo / config_name
            config_path.write_text("[config]\ntest = true")

            configs = discovery.discover_configs(["src/main.py"])
            assert len(configs) == 1
            assert configs[0].path == config_path

            # Clean up for next iteration
            config_path.unlink()

    def test_config_precedence(self, temp_repo, discovery):
        """Test that first config name in precedence list wins."""
        # Create multiple config files - only first should be found
        (temp_repo / ".pr_agent.toml").write_text("[config]\ntest = 1")
        (temp_repo / "pr_agent.toml").write_text("[config]\ntest = 2")

        configs = discovery.discover_configs(["src/main.py"])

        assert len(configs) == 1
        assert configs[0].path == temp_repo / ".pr_agent.toml"

    def test_max_depth_limit(self, temp_repo):
        """Test that max_depth limit is enforced."""
        # Create deep nested structure
        deep_path = temp_repo / "a" / "b" / "c" / "d" / "e" / "f"
        deep_path.mkdir(parents=True)
        (deep_path / "file.py").touch()

        # Create configs at various depths
        (temp_repo / ".pr_agent.toml").write_text("[config]\ndepth = 0")
        (temp_repo / "a" / ".pr_agent.toml").write_text("[config]\ndepth = 1")
        (temp_repo / "a" / "b" / "c" / ".pr_agent.toml").write_text("[config]\ndepth = 3")
        (temp_repo / "a" / "b" / "c" / "d" / "e" / ".pr_agent.toml").write_text("[config]\ndepth = 5")
        (temp_repo / "a" / "b" / "c" / "d" / "e" / "f" / ".pr_agent.toml").write_text("[config]\ndepth = 6")

        # With max_depth=5, should stop before the deepest config
        discovery = ConfigDiscovery(temp_repo, max_depth=5)
        configs = discovery.discover_configs(["a/b/c/d/e/f/file.py"])

        # Should find root + configs within depth limit
        depths = [c.depth for c in configs]
        assert max(depths) <= 5

    def test_cache_functionality(self, temp_repo, discovery):
        """Test that discovery results are cached."""
        # Create config
        (temp_repo / ".pr_agent.toml").write_text("[config]\nmodel = 'gpt-4'")

        changed_files = ["src/backend/main.py"]

        # First call
        configs1 = discovery.discover_configs(changed_files)
        cache_size1 = discovery.get_cache_size()

        # Second call with same files should use cache
        configs2 = discovery.discover_configs(changed_files)
        cache_size2 = discovery.get_cache_size()

        assert configs1 == configs2
        assert cache_size1 == 1
        assert cache_size2 == 1  # Cache should still have 1 entry

    def test_clear_cache(self, temp_repo, discovery):
        """Test cache clearing."""
        (temp_repo / ".pr_agent.toml").write_text("[config]\nmodel = 'gpt-4'")

        discovery.discover_configs(["src/main.py"])
        assert discovery.get_cache_size() > 0

        discovery.clear_cache()
        assert discovery.get_cache_size() == 0

    def test_no_configs_found(self, temp_repo, discovery):
        """Test behavior when no config files exist."""
        configs = discovery.discover_configs(["src/backend/main.py"])
        assert len(configs) == 0

    def test_config_outside_repo(self, temp_repo, discovery):
        """Test that configs outside repo are ignored."""
        # Create a config outside repo
        parent = temp_repo.parent
        (parent / ".pr_agent.toml").write_text("[config]\ntest = true")

        configs = discovery.discover_configs(["src/main.py"])

        # Should not find the parent config
        assert all(discovery._is_within_repo(c.path.parent) for c in configs)

        # Cleanup
        (parent / ".pr_agent.toml").unlink()

    def test_multiple_files_discovery(self, temp_repo, discovery):
        """Test discovery with multiple changed files."""
        # Create configs in different branches
        (temp_repo / ".pr_agent.toml").write_text("[config]\nroot = true")
        (temp_repo / "src" / "backend" / ".pr_agent.toml").write_text("[config]\nbackend = true")
        (temp_repo / "src" / "frontend" / ".pr_agent.toml").write_text("[config]\nfrontend = true")

        changed_files = [
            "src/backend/main.py",
            "src/frontend/app.tsx"
        ]

        configs = discovery.discover_configs(changed_files)

        # Should find root + both subdirectory configs
        assert len(configs) >= 2
        config_paths = [str(c.relative_path) for c in configs]
        assert ".pr_agent.toml" in config_paths  # root

    def test_config_file_hashable(self):
        """Test that ConfigFile objects are hashable."""
        config1 = ConfigFile(Path("/test/.pr_agent.toml"), depth=0, relative_path=Path(".pr_agent.toml"))
        config2 = ConfigFile(Path("/test/.pr_agent.toml"), depth=0, relative_path=Path(".pr_agent.toml"))

        # Should be usable in sets
        config_set = {config1, config2}
        assert len(config_set) == 1

    def test_config_file_equality(self):
        """Test ConfigFile equality comparison."""
        config1 = ConfigFile(Path("/test/.pr_agent.toml"), depth=0, relative_path=Path(".pr_agent.toml"))
        config2 = ConfigFile(Path("/test/.pr_agent.toml"), depth=0, relative_path=Path(".pr_agent.toml"))
        config3 = ConfigFile(Path("/test2/.pr_agent.toml"), depth=0, relative_path=Path(".pr_agent.toml"))

        assert config1 == config2
        assert config1 != config3
        assert config1 != "not a config"
