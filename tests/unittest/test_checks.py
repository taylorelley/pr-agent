# AGPL-3.0 License

"""
Unit tests for PR checks module.
"""

import pytest
from pr_agent.checks.check_context import CheckContext
from pr_agent.checks.built_in_checks import (
    PatternCheck,
    FileSizeCheck,
    RequiredFilesCheck,
    ForbiddenPatternsCheck,
)
from pr_agent.algo.types import FilePatchInfo, EDIT_TYPE


@pytest.mark.asyncio
class TestPatternCheck:
    """Tests for PatternCheck."""

    async def test_pattern_found(self):
        """Test that pattern check fails when forbidden pattern is found."""
        check = PatternCheck(
            name="no_console_logs",
            description="Forbid console.log",
            pattern=r"console\.log",
            message="Remove console.log statements"
        )

        patch_with_console = """+console.log('debug');"""
        context = CheckContext(
            pr_url="test",
            pr_title="Test PR",
            pr_description="Test",
            pr_author="test",
            files_changed=["test.js"],
            patches=[FilePatchInfo(
                base_file="", head_file="", patch=patch_with_console,
                filename="test.js", edit_type=EDIT_TYPE.MODIFIED
            )]
        )

        # Filter context for this check
        context = check.filter_context(context)

        result = await check.run(context)

        assert not result.passed
        assert len(result.details) > 0
        assert "console.log" in result.message.lower()

    async def test_pattern_not_found(self):
        """Test that pattern check passes when forbidden pattern is not found."""
        check = PatternCheck(
            name="no_console_logs",
            description="Forbid console.log",
            pattern=r"console\.log",
            message="Remove console.log statements"
        )

        patch_without_console = """+logger.info('debug');"""
        context = CheckContext(
            pr_url="test",
            pr_title="Test PR",
            pr_description="Test",
            pr_author="test",
            files_changed=["test.js"],
            patches=[FilePatchInfo(
                base_file="", head_file="", patch=patch_without_console,
                filename="test.js", edit_type=EDIT_TYPE.MODIFIED
            )]
        )

        context = check.filter_context(context)
        result = await check.run(context)

        assert result.passed
        assert len(result.details) == 0

    async def test_required_pattern(self):
        """Test pattern check with invert=True (require pattern)."""
        check = PatternCheck(
            name="require_license",
            description="Require license header",
            pattern=r"# AGPL-3.0 License",
            message="License header required",
            invert=True
        )

        patch_with_license = """
+# AGPL-3.0 License
+def main():
+    pass
"""
        context = CheckContext(
            pr_url="test",
            pr_title="Test PR",
            pr_description="Test",
            pr_author="test",
            files_changed=["test.py"],
            patches=[FilePatchInfo(
                base_file="", head_file="", patch=patch_with_license,
                filename="test.py", edit_type=EDIT_TYPE.ADDED
            )]
        )

        context = check.filter_context(context)
        result = await check.run(context)

        assert result.passed


@pytest.mark.asyncio
class TestFileSizeCheck:
    """Tests for FileSizeCheck."""

    async def test_pr_size_within_limit(self):
        """Test that PR passes when under line limit."""
        check = FileSizeCheck(
            name="pr_size",
            description="Check PR size",
            max_pr_lines=100
        )

        small_patch = "+line1\n+line2\n+line3\n-oldline"
        context = CheckContext(
            pr_url="test",
            pr_title="Test PR",
            pr_description="Test",
            pr_author="test",
            files_changed=["test.txt"],
            patches=[FilePatchInfo(
                base_file="", head_file="", patch=small_patch,
                filename="test.txt", edit_type=EDIT_TYPE.MODIFIED,
                num_plus_lines=3, num_minus_lines=1
            )]
        )

        context = check.filter_context(context)
        result = await check.run(context)

        assert result.passed

    async def test_pr_size_exceeds_limit(self):
        """Test that PR fails when exceeding line limit."""
        check = FileSizeCheck(
            name="pr_size",
            description="Check PR size",
            max_pr_lines=5
        )

        # Create a patch with 10 lines changed
        context = CheckContext(
            pr_url="test",
            pr_title="Test PR",
            pr_description="Test",
            pr_author="test",
            files_changed=["test.txt"],
            patches=[FilePatchInfo(
                base_file="", head_file="", patch="",
                filename="test.txt", edit_type=EDIT_TYPE.MODIFIED,
                num_plus_lines=8, num_minus_lines=2
            )]
        )

        context = check.filter_context(context)
        result = await check.run(context)

        assert not result.passed
        assert len(result.details) > 0


@pytest.mark.asyncio
class TestRequiredFilesCheck:
    """Tests for RequiredFilesCheck."""

    async def test_required_files_present(self):
        """Test that check passes when required files are modified."""
        check = RequiredFilesCheck(
            name="package_json_lock",
            description="Require package-lock.json when package.json changes",
            trigger_files=["package.json"],
            required_files=["package-lock.json"]
        )

        context = CheckContext(
            pr_url="test",
            pr_title="Test PR",
            pr_description="Test",
            pr_author="test",
            files_changed=["package.json", "package-lock.json"],
            patches=[]
        )

        context = check.filter_context(context)
        result = await check.run(context)

        assert result.passed

    async def test_required_files_missing(self):
        """Test that check fails when required files are missing."""
        check = RequiredFilesCheck(
            name="package_json_lock",
            description="Require package-lock.json when package.json changes",
            trigger_files=["package.json"],
            required_files=["package-lock.json"]
        )

        context = CheckContext(
            pr_url="test",
            pr_title="Test PR",
            pr_description="Test",
            pr_author="test",
            files_changed=["package.json"],  # Missing package-lock.json
            patches=[]
        )

        context = check.filter_context(context)
        result = await check.run(context)

        assert not result.passed
        assert len(result.details) > 0

    async def test_trigger_not_matched(self):
        """Test that check passes when trigger files are not modified."""
        check = RequiredFilesCheck(
            name="package_json_lock",
            description="Require package-lock.json when package.json changes",
            trigger_files=["package.json"],
            required_files=["package-lock.json"]
        )

        context = CheckContext(
            pr_url="test",
            pr_title="Test PR",
            pr_description="Test",
            pr_author="test",
            files_changed=["src/index.js"],  # No package.json, so check doesn't apply
            patches=[]
        )

        context = check.filter_context(context)
        result = await check.run(context)

        assert result.passed


@pytest.mark.asyncio
class TestForbiddenPatternsCheck:
    """Tests for ForbiddenPatternsCheck."""

    async def test_api_key_detected(self):
        """Test that API key is detected."""
        check = ForbiddenPatternsCheck(
            name="no_secrets",
            description="Prevent secrets in code"
        )

        # Use a pattern that looks like an API key but won't trigger GitHub's secret scanning
        patch_with_secret = """+API_KEY = "test_abc123def456ghi789jkl012mno345pqr678"
+print(API_KEY)
"""
        context = CheckContext(
            pr_url="test",
            pr_title="Test PR",
            pr_description="Test",
            pr_author="test",
            files_changed=["config.py"],
            patches=[FilePatchInfo(
                base_file="", head_file="", patch=patch_with_secret,
                filename="config.py", edit_type=EDIT_TYPE.MODIFIED
            )]
        )

        context = check.filter_context(context)
        result = await check.run(context)

        assert not result.passed
        assert result.severity == "error"
        assert len(result.details) > 0

    async def test_no_secrets_found(self):
        """Test that check passes when no secrets are found."""
        check = ForbiddenPatternsCheck(
            name="no_secrets",
            description="Prevent secrets in code"
        )

        clean_patch = """+def get_api_key():
+    return os.environ.get('API_KEY')
"""
        context = CheckContext(
            pr_url="test",
            pr_title="Test PR",
            pr_description="Test",
            pr_author="test",
            files_changed=["config.py"],
            patches=[FilePatchInfo(
                base_file="", head_file="", patch=clean_patch,
                filename="config.py", edit_type=EDIT_TYPE.MODIFIED
            )]
        )

        context = check.filter_context(context)
        result = await check.run(context)

        assert result.passed

    async def test_private_key_detected(self):
        """Test that private key is detected."""
        check = ForbiddenPatternsCheck(
            name="no_secrets",
            description="Prevent secrets in code"
        )

        patch_with_key = """+-----BEGIN PRIVATE KEY-----
+MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7VJTUt9Us8cKj
+-----END PRIVATE KEY-----
"""
        context = CheckContext(
            pr_url="test",
            pr_title="Test PR",
            pr_description="Test",
            pr_author="test",
            files_changed=["key.pem"],
            patches=[FilePatchInfo(
                base_file="", head_file="", patch=patch_with_key,
                filename="key.pem", edit_type=EDIT_TYPE.ADDED
            )]
        )

        context = check.filter_context(context)
        result = await check.run(context)

        assert not result.passed
        assert "private key" in result.details[0].message.lower()
