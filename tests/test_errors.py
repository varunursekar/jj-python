"""Tests for the error hierarchy."""

from jj.errors import JJCommandError, JJError, JJNotFoundError, JJRepoNotFoundError


class TestErrorHierarchy:
    def test_jj_error_is_exception(self):
        assert issubclass(JJError, Exception)

    def test_jj_not_found_inherits_jj_error(self):
        assert issubclass(JJNotFoundError, JJError)

    def test_jj_command_error_inherits_jj_error(self):
        assert issubclass(JJCommandError, JJError)

    def test_jj_repo_not_found_inherits_command_error(self):
        assert issubclass(JJRepoNotFoundError, JJCommandError)


class TestJJNotFoundError:
    def test_default_path(self):
        err = JJNotFoundError()
        assert err.jj_path == "jj"
        assert "jj" in str(err)

    def test_custom_path(self):
        err = JJNotFoundError("/custom/jj")
        assert err.jj_path == "/custom/jj"
        assert "/custom/jj" in str(err)

    def test_is_catchable_as_jj_error(self):
        try:
            raise JJNotFoundError()
        except JJError:
            pass  # expected


class TestJJCommandError:
    def test_attributes(self):
        err = JJCommandError(["jj", "log"], 1, "something went wrong")
        assert err.command == ["jj", "log"]
        assert err.exit_code == 1
        assert err.stderr == "something went wrong"

    def test_message_includes_command(self):
        err = JJCommandError(["jj", "status"], 2, "oops")
        msg = str(err)
        assert "jj status" in msg
        assert "exit 2" in msg
        assert "oops" in msg

    def test_is_catchable_as_jj_error(self):
        try:
            raise JJCommandError(["jj"], 1, "")
        except JJError:
            pass  # expected


class TestJJRepoNotFoundError:
    def test_inherits_command_error_attrs(self):
        err = JJRepoNotFoundError(["jj", "log"], 1, "No repo found")
        assert err.command == ["jj", "log"]
        assert err.exit_code == 1
        assert err.stderr == "No repo found"

    def test_catchable_as_command_error(self):
        try:
            raise JJRepoNotFoundError(["jj"], 1, "")
        except JJCommandError:
            pass  # expected
