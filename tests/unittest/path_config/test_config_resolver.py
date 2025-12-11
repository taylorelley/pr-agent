"""
Unit tests for ConfigResolver class.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from pr_agent.path_config.config_resolver import ConfigResolver, ResolvedConfig


class TestConfigResolver:
    """Test suite for ConfigResolver class."""

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
    def resolver(self, temp_repo):
        """Create a ConfigResolver instance."""
        return ConfigResolver(temp_repo, max_depth=5, enable_path_config=True)

    def test_init(self, temp_repo):
        """Test ConfigResolver initialization."""
        resolver = ConfigResolver(temp_repo, max_depth=3, enable_path_config=True)
        assert resolver.repo_root == temp_repo.resolve()
        assert resolver.max_depth == 3
        assert resolver.enable_path_config is True
        assert len(resolver._resolution_cache) == 0

    def test_disabled_path_config(self, temp_repo):
        """Test behavior when path config is disabled."""
        resolver = ConfigResolver(temp_repo, enable_path_config=False)

        result = resolver.get_config_for_file("src/main.py")

        assert isinstance(result, ResolvedConfig)
        assert result.config == {}
        assert len(result.source_configs) == 0

    def test_get_config_for_file_no_configs(self, temp_repo, resolver):
        """Test getting config when no config files exist."""
        result = resolver.get_config_for_file("src/backend/main.py")

        assert isinstance(result, ResolvedConfig)
        assert result.file_path == "src/backend/main.py"
        assert len(result.source_configs) == 0

    def test_get_config_for_file_with_root_config(self, temp_repo, resolver):
        """Test getting config with only root configuration."""
        # Create root config
        (temp_repo / ".pr_agent.toml").write_text("""
[config]
model = "gpt-4"

[pr_reviewer]
num_max_findings = 5
        """)

        result = resolver.get_config_for_file("src/backend/main.py")

        assert len(result.source_configs) == 1
        assert result.config["config"]["model"] == "gpt-4"
        assert result.config["pr_reviewer"]["num_max_findings"] == 5

    def test_get_config_for_file_with_nested_configs(self, temp_repo, resolver):
        """Test getting config with nested configurations."""
        # Create configs at different levels
        (temp_repo / ".pr_agent.toml").write_text("""
[pr_reviewer]
num_max_findings = 3
extra_instructions = "root"
        """)

        (temp_repo / "src" / ".pr_agent.toml").write_text("""
[pr_reviewer]
extra_instructions = "src level"
        """)

        (temp_repo / "src" / "backend" / ".pr_agent.toml").write_text("""
[pr_reviewer]
extra_instructions = "backend level"
        """)

        result = resolver.get_config_for_file("src/backend/main.py")

        # Should have all three configs
        assert len(result.source_configs) == 3

        # Most specific (backend) should win
        assert result.config["pr_reviewer"]["extra_instructions"] == "backend level"
        # But root value should be preserved if not overridden
        assert result.config["pr_reviewer"]["num_max_findings"] == 3

    def test_get_config_for_files_batch(self, temp_repo, resolver):
        """Test getting configs for multiple files at once."""
        # Create configs
        (temp_repo / ".pr_agent.toml").write_text("""
[pr_reviewer]
num_max_findings = 3
        """)

        (temp_repo / "src" / "backend" / ".pr_agent.toml").write_text("""
[pr_reviewer]
extra_instructions = "backend"
        """)

        (temp_repo / "src" / "frontend" / ".pr_agent.toml").write_text("""
[pr_reviewer]
extra_instructions = "frontend"
        """)

        file_paths = [
            "src/backend/main.py",
            "src/frontend/app.tsx"
        ]

        results = resolver.get_config_for_files(file_paths)

        assert len(results) == 2
        assert "src/backend/main.py" in results
        assert "src/frontend/app.tsx" in results

        # Each should have different effective config
        backend_config = results["src/backend/main.py"]
        frontend_config = results["src/frontend/app.tsx"]

        assert backend_config.config["pr_reviewer"]["extra_instructions"] == "backend"
        assert frontend_config.config["pr_reviewer"]["extra_instructions"] == "frontend"

    def test_cache_functionality(self, temp_repo, resolver):
        """Test that resolved configs are cached."""
        (temp_repo / ".pr_agent.toml").write_text("""
[pr_reviewer]
num_max_findings = 3
        """)

        file_path = "src/backend/main.py"

        # First call
        result1 = resolver.get_config_for_file(file_path)

        # Second call should use cache
        result2 = resolver.get_config_for_file(file_path)

        assert result1 is result2  # Should be same object from cache

    def test_clear_cache(self, temp_repo, resolver):
        """Test cache clearing."""
        (temp_repo / ".pr_agent.toml").write_text("""
[pr_reviewer]
num_max_findings = 3
        """)

        resolver.get_config_for_file("src/main.py")

        # Cache should have entries
        assert len(resolver._resolution_cache) > 0

        resolver.clear_cache()

        # Cache should be empty
        assert len(resolver._resolution_cache) == 0
        # Discovery cache should also be cleared
        assert resolver.discovery.get_cache_size() == 0

    def test_get_effective_setting(self, temp_repo, resolver):
        """Test getting a specific setting value for a file."""
        (temp_repo / ".pr_agent.toml").write_text("""
[pr_reviewer]
num_max_findings = 5
extra_instructions = "test"
        """)

        value = resolver.get_effective_setting(
            "src/main.py",
            "pr_reviewer.num_max_findings"
        )

        assert value == 5

    def test_get_effective_setting_with_default(self, resolver):
        """Test getting setting with default value."""
        value = resolver.get_effective_setting(
            "src/main.py",
            "nonexistent.setting",
            default="default_value"
        )

        assert value == "default_value"

    def test_validate_all_configs(self, temp_repo, resolver):
        """Test validation of all configurations."""
        # Create valid config
        (temp_repo / ".pr_agent.toml").write_text("""
[pr_reviewer]
num_max_findings = 3
        """)

        issues = resolver.validate_all_configs(["src/main.py"])

        assert len(issues) == 0

    def test_validate_all_configs_with_issues(self, temp_repo, resolver):
        """Test validation with configuration issues."""
        # Create invalid child config
        (temp_repo / "src").mkdir(exist_ok=True)
        (temp_repo / "src" / ".pr_agent.toml").write_text("""
[config]
model = "forbidden"  # Not allowed in subdirectory
        """)

        issues = resolver.validate_all_configs(["src/main.py"])

        assert len(issues) > 0

    def test_get_config_summary(self, temp_repo, resolver):
        """Test getting configuration summary."""
        # Create configs
        (temp_repo / ".pr_agent.toml").write_text("""
[pr_reviewer]
num_max_findings = 3
        """)

        (temp_repo / "src").mkdir(exist_ok=True)
        (temp_repo / "src" / ".pr_agent.toml").write_text("""
[pr_reviewer]
extra_instructions = "src"
        """)

        changed_files = ["src/main.py"]
        summary = resolver.get_config_summary(changed_files)

        assert summary["path_config_enabled"] is True
        assert "repo_root" in summary
        assert summary["max_depth"] == 5
        assert len(summary["discovered_configs"]) == 2
        assert summary["changed_files_count"] == 1

    def test_resolved_config_info(self, temp_repo, resolver):
        """Test ResolvedConfig.get_applied_config_info method."""
        (temp_repo / ".pr_agent.toml").write_text("""
[pr_reviewer]
num_max_findings = 3
        """)

        result = resolver.get_config_for_file("src/main.py")

        info = result.get_applied_config_info()

        assert "Applied configs:" in info or "global configuration" in info

    def test_resolved_config_no_sources(self):
        """Test ResolvedConfig info with no source configs."""
        resolved = ResolvedConfig(
            config={},
            source_configs=[],
            file_path="test.py"
        )

        info = resolved.get_applied_config_info()

        assert "global configuration" in info

    def test_filter_applicable_configs(self, temp_repo, resolver):
        """Test filtering configs applicable to a specific file."""
        # Create configs at different levels
        (temp_repo / ".pr_agent.toml").write_text("[config]\nroot = true")
        (temp_repo / "src").mkdir(exist_ok=True)
        (temp_repo / "src" / ".pr_agent.toml").write_text("[config]\nsrc = true")
        (temp_repo / "tests").mkdir(exist_ok=True)
        (temp_repo / "tests" / ".pr_agent.toml").write_text("[config]\ntests = true")

        # For a file in src, should only get root and src configs
        result = resolver.get_config_for_file("src/main.py")

        # Should not include tests config
        config_paths = [str(c.relative_path) for c in result.source_configs]
        # Verify tests config is NOT included
        assert not any("tests" in path for path in config_paths)
        # Root config should be applicable
        assert any(".pr_agent.toml" == path for path in config_paths)

    def test_get_config_for_files_disabled(self, temp_repo):
        """Test batch config retrieval when path config is disabled."""
        resolver = ConfigResolver(temp_repo, enable_path_config=False)

        file_paths = ["src/main.py", "tests/test.py"]
        results = resolver.get_config_for_files(file_paths)

        assert len(results) == 2
        for result in results.values():
            assert result.config == {}

    def test_get_config_for_files_empty_list(self, temp_repo, resolver):
        """Test batch config retrieval with empty file list."""
        results = resolver.get_config_for_files([])

        assert results == {}

    def test_effective_setting_nested_path(self, temp_repo, resolver):
        """Test getting deeply nested setting."""
        (temp_repo / ".pr_agent.toml").write_text("""
[config]
model = "gpt-4"

[pr_reviewer]
extra_instructions = "test"
        """)

        # Test existing nested setting
        value = resolver.get_effective_setting(
            "src/main.py",
            "config.model"
        )

        assert value == "gpt-4"

    def test_effective_setting_case_insensitive(self, temp_repo, resolver):
        """Test that settings are case-insensitive."""
        (temp_repo / ".pr_agent.toml").write_text("""
[pr_reviewer]
num_max_findings = 7
        """)

        # Try with different cases
        value = resolver.get_effective_setting(
            "src/main.py",
            "PR_REVIEWER.NUM_MAX_FINDINGS"
        )

        # Should find the setting and return the correct value
        assert value == 7
