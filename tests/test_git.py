"""Tests for GitManager."""

from unittest.mock import patch

import pytest

from jj.errors import JJCommandError

from .conftest import MockExecutor, make_repo


@pytest.fixture
def mx():
    return MockExecutor()


@pytest.fixture
def gm(mx):
    rp = make_repo(mx)
    return rp.git, mx


class TestGitPush:
    @pytest.mark.asyncio
    async def test_push_basic(self, gm):
        mgr, mx = gm
        mx.queue(stdout="ok", stderr="")
        result = await mgr.push()
        cmd = mx.calls[0]
        assert "git" in cmd
        assert "push" in cmd

    @pytest.mark.asyncio
    async def test_push_with_remote(self, gm):
        mgr, mx = gm
        mx.queue(stdout="", stderr="")
        await mgr.push(remote="upstream")
        cmd = mx.calls[0]
        assert "--remote" in cmd
        idx = cmd.index("--remote")
        assert cmd[idx + 1] == "upstream"

    @pytest.mark.asyncio
    async def test_push_with_bookmark(self, gm):
        mgr, mx = gm
        mx.queue(stdout="", stderr="")
        await mgr.push(bookmark="main")
        assert "-b" in mx.calls[0]

    @pytest.mark.asyncio
    async def test_push_all(self, gm):
        mgr, mx = gm
        mx.queue(stdout="", stderr="")
        await mgr.push(all_bookmarks=True)
        assert "--all" in mx.calls[0]

    @pytest.mark.asyncio
    async def test_push_with_change(self, gm):
        mgr, mx = gm
        mx.queue(stdout="", stderr="")
        await mgr.push(change="abc")
        cmd = mx.calls[0]
        assert "-c" in cmd
        idx = cmd.index("-c")
        assert cmd[idx + 1] == "abc"


class TestGitFetch:
    @pytest.mark.asyncio
    async def test_fetch_basic(self, gm):
        mgr, mx = gm
        mx.queue(stdout="", stderr="")
        await mgr.fetch()
        cmd = mx.calls[0]
        assert "git" in cmd
        assert "fetch" in cmd

    @pytest.mark.asyncio
    async def test_fetch_with_remote(self, gm):
        mgr, mx = gm
        mx.queue(stdout="", stderr="")
        await mgr.fetch(remote="upstream")
        assert "--remote" in mx.calls[0]

    @pytest.mark.asyncio
    async def test_fetch_all_remotes(self, gm):
        mgr, mx = gm
        mx.queue(stdout="", stderr="")
        await mgr.fetch(all_remotes=True)
        assert "--all-remotes" in mx.calls[0]


class TestGitClone:
    @pytest.mark.asyncio
    async def test_clone_basic(self):
        mx = MockExecutor()
        mx.queue(stdout="")  # clone command
        with patch("jj._runner.shutil.which", return_value="/usr/bin/jj"):
            from jj._git import GitManager
            repo = await GitManager.clone(
                "https://github.com/user/repo.git",
                "/tmp/test-clone",
                executor=mx,
            )
        cmd = mx.calls[0]
        assert "git" in cmd
        assert "clone" in cmd
        assert "https://github.com/user/repo.git" in cmd
        assert "/tmp/test-clone" in cmd

    @pytest.mark.asyncio
    async def test_clone_deduces_path_from_url(self):
        mx = MockExecutor()
        mx.queue(stdout="")
        with patch("jj._runner.shutil.which", return_value="/usr/bin/jj"):
            from jj._git import GitManager
            repo = await GitManager.clone(
                "https://github.com/user/myrepo.git",
                executor=mx,
            )
        # Should deduce "myrepo" from URL
        assert repo._runner.repo_path is not None
        assert "myrepo" in str(repo._runner.repo_path)

    @pytest.mark.asyncio
    async def test_clone_deduces_path_no_git_suffix(self):
        mx = MockExecutor()
        mx.queue(stdout="")
        with patch("jj._runner.shutil.which", return_value="/usr/bin/jj"):
            from jj._git import GitManager
            repo = await GitManager.clone(
                "https://github.com/user/myrepo",
                executor=mx,
            )
        assert "myrepo" in str(repo._runner.repo_path)


class TestGitRemote:
    @pytest.mark.asyncio
    async def test_remote_add(self, gm):
        mgr, mx = gm
        mx.queue(stdout="")
        await mgr.remote_add("upstream", "https://example.com/repo.git")
        cmd = mx.calls[0]
        assert "git" in cmd
        assert "remote" in cmd
        assert "add" in cmd
        assert "upstream" in cmd
        assert "https://example.com/repo.git" in cmd

    @pytest.mark.asyncio
    async def test_remote_remove(self, gm):
        mgr, mx = gm
        mx.queue(stdout="")
        await mgr.remote_remove("upstream")
        cmd = mx.calls[0]
        assert "remove" in cmd
        assert "upstream" in cmd

    @pytest.mark.asyncio
    async def test_remote_rename(self, gm):
        mgr, mx = gm
        mx.queue(stdout="")
        await mgr.remote_rename("old", "new")
        cmd = mx.calls[0]
        assert "rename" in cmd
        assert "old" in cmd
        assert "new" in cmd

    @pytest.mark.asyncio
    async def test_remote_list_parses_output(self, gm):
        mgr, mx = gm
        mx.queue(stdout="origin https://github.com/user/repo.git\nupstream https://other.com/repo\n")
        result = await mgr.remote_list()
        assert result == {
            "origin": "https://github.com/user/repo.git",
            "upstream": "https://other.com/repo",
        }

    @pytest.mark.asyncio
    async def test_remote_list_empty(self, gm):
        mgr, mx = gm
        mx.queue(stdout="")
        result = await mgr.remote_list()
        assert result == {}

    @pytest.mark.asyncio
    async def test_remote_set_url(self, gm):
        mgr, mx = gm
        mx.queue(stdout="")
        await mgr.remote_set_url("origin", "https://new-url.com/repo.git")
        cmd = mx.calls[0]
        assert "set-url" in cmd
        assert "origin" in cmd


class TestGitExportImport:
    @pytest.mark.asyncio
    async def test_export(self, gm):
        mgr, mx = gm
        mx.queue(stdout="")
        await mgr.export()
        cmd = mx.calls[0]
        assert "git" in cmd
        assert "export" in cmd

    @pytest.mark.asyncio
    async def test_import(self, gm):
        mgr, mx = gm
        mx.queue(stdout="")
        await mgr.import_()
        cmd = mx.calls[0]
        assert "git" in cmd
        assert "import" in cmd


class TestGitBundle:
    @pytest.mark.asyncio
    async def test_bundle_create_default_all(self, gm):
        mgr, mx = gm
        # export
        mx.queue(stdout="")
        # workspace root
        mx.queue(stdout="/repo\n")
        # git bundle create
        mx.queue(stdout="", returncode=0)
        result = await mgr.bundle_create("/tmp/bundle.pack")
        assert result == "/tmp/bundle.pack"
        # First call: jj git export
        assert "export" in mx.calls[0]
        # Second call: jj workspace root
        assert "root" in mx.calls[1]
        # Third call: git bundle create
        git_cmd = mx.calls[2]
        assert "git" in git_cmd
        assert "bundle" in git_cmd
        assert "create" in git_cmd
        assert "--all" in git_cmd

    @pytest.mark.asyncio
    async def test_bundle_create_specific_refs(self, gm):
        mgr, mx = gm
        mx.queue(stdout="")  # export
        mx.queue(stdout="/repo\n")  # workspace root
        mx.queue(stdout="", returncode=0)  # git bundle create
        await mgr.bundle_create("/tmp/bundle.pack", refs=["main", "dev"])
        git_cmd = mx.calls[2]
        assert "--all" not in git_cmd
        assert "main" in git_cmd
        assert "dev" in git_cmd

    @pytest.mark.asyncio
    async def test_bundle_create_error(self, gm):
        mgr, mx = gm
        mx.queue(stdout="")  # export
        mx.queue(stdout="/repo\n")  # workspace root
        mx.queue(returncode=1, stderr="bundle error")  # git bundle create fails
        with pytest.raises(JJCommandError):
            await mgr.bundle_create("/tmp/bad.pack")

    @pytest.mark.asyncio
    async def test_bundle_unbundle(self, gm):
        mgr, mx = gm
        # workspace root (for _git_cmd)
        mx.queue(stdout="/repo\n")
        # git fetch
        mx.queue(stdout="", returncode=0)
        # jj git import
        mx.queue(stdout="")
        await mgr.bundle_unbundle("/tmp/bundle.pack")
        # git fetch call
        git_cmd = mx.calls[1]
        assert "fetch" in git_cmd
        assert "/tmp/bundle.pack" in git_cmd
        # import call
        assert "import" in mx.calls[2]

    @pytest.mark.asyncio
    async def test_bundle_unbundle_error(self, gm):
        mgr, mx = gm
        mx.queue(stdout="/repo\n")  # workspace root
        mx.queue(returncode=1, stderr="fetch error")  # git fetch fails
        with pytest.raises(JJCommandError):
            await mgr.bundle_unbundle("/tmp/bad.pack")

    @pytest.mark.asyncio
    async def test_bundle_verify(self, gm):
        mgr, mx = gm
        mx.queue(stdout="/repo\n")  # workspace root
        mx.queue(stdout="ok\n", stderr="verified\n", returncode=0)
        result = await mgr.bundle_verify("/tmp/bundle.pack")
        assert "ok" in result
        assert "verified" in result

    @pytest.mark.asyncio
    async def test_bundle_verify_error(self, gm):
        mgr, mx = gm
        mx.queue(stdout="/repo\n")  # workspace root
        mx.queue(returncode=1, stderr="bad bundle")
        with pytest.raises(JJCommandError):
            await mgr.bundle_verify("/tmp/bad.pack")
