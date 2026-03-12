"""
Tests for scheduler.run — all external calls mocked.
"""

import pytest
from unittest.mock import MagicMock, patch

import scheduler.run as run_module

PATCH_RUN_PIPELINE = "scheduler.run.run_pipeline"
PATCH_COMPOSE = "scheduler.run.compose"
PATCH_SEND_EMAIL = "scheduler.run.send_email"
PATCH_RECIPIENT = "scheduler.run.SCHEDULER_RECIPIENT_EMAIL"
PATCH_RECIPIENT_NAME = "scheduler.run.SCHEDULER_RECIPIENT_NAME"
PATCH_WEEKS = "scheduler.run.SCHEDULER_WEEKS"
PATCH_MAX_REVIEWS = "scheduler.run.SCHEDULER_MAX_REVIEWS"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pipeline_result():
    result = MagicMock()
    result.pulse_markdown = "# Weekly Pulse\nTOP THEMES\n..."
    result.week_label = "Week of 2026-03-09"
    result.review_count = 120
    result.theme_count = 3
    return result


def _run_main(recipient="pulse@example.com", name="Product Team", weeks=3, max_reviews=200):
    """Helper: patch all externals and call main()."""
    pipeline_result = _make_pipeline_result()
    fake_msg = MagicMock()
    with patch(PATCH_RECIPIENT, recipient), \
         patch(PATCH_RECIPIENT_NAME, name), \
         patch(PATCH_WEEKS, weeks), \
         patch(PATCH_MAX_REVIEWS, max_reviews), \
         patch(PATCH_RUN_PIPELINE, return_value=pipeline_result) as mock_pipeline, \
         patch(PATCH_COMPOSE, return_value=fake_msg) as mock_compose, \
         patch(PATCH_SEND_EMAIL) as mock_send, \
         patch("scheduler.run.os.getenv", return_value="sender@gmail.com"):
        run_module.main()
    return mock_pipeline, mock_compose, mock_send, pipeline_result, fake_msg


# ---------------------------------------------------------------------------
# main() — missing recipient guard
# ---------------------------------------------------------------------------

class TestMainMissingRecipient:
    def test_exits_when_recipient_empty(self):
        with patch(PATCH_RECIPIENT, ""), \
             patch(PATCH_RUN_PIPELINE) as mock_pipeline:
            with pytest.raises(SystemExit) as exc_info:
                run_module.main()
        assert exc_info.value.code == 1
        mock_pipeline.assert_not_called()


# ---------------------------------------------------------------------------
# main() — happy path
# ---------------------------------------------------------------------------

class TestMainHappyPath:
    def test_run_pipeline_called(self):
        mock_pipeline, _, _, _, _ = _run_main()
        mock_pipeline.assert_called_once()

    def test_run_pipeline_uses_scheduler_weeks(self):
        mock_pipeline, _, _, _, _ = _run_main(weeks=3)
        assert mock_pipeline.call_args[1]["weeks"] == 3

    def test_run_pipeline_uses_scheduler_max_reviews(self):
        mock_pipeline, _, _, _, _ = _run_main(max_reviews=200)
        assert mock_pipeline.call_args[1]["max_reviews"] == 200

    def test_run_pipeline_receives_progress_callback(self):
        mock_pipeline, _, _, _, _ = _run_main()
        assert callable(mock_pipeline.call_args[1].get("on_progress"))

    def test_compose_called_with_pulse_markdown(self):
        _, mock_compose, _, pipeline_result, _ = _run_main()
        assert mock_compose.call_args[1]["markdown"] == pipeline_result.pulse_markdown

    def test_compose_called_with_week_label(self):
        _, mock_compose, _, pipeline_result, _ = _run_main()
        assert mock_compose.call_args[1]["week_label"] == pipeline_result.week_label

    def test_compose_called_with_recipient_email(self):
        _, mock_compose, _, _, _ = _run_main(recipient="pulse@example.com")
        assert mock_compose.call_args[1]["recipient_email"] == "pulse@example.com"

    def test_compose_called_with_recipient_name(self):
        _, mock_compose, _, _, _ = _run_main(name="Product Team")
        assert mock_compose.call_args[1]["recipient_name"] == "Product Team"

    def test_send_email_called_with_composed_message(self):
        _, _, mock_send, _, fake_msg = _run_main()
        mock_send.assert_called_once_with(fake_msg)


# ---------------------------------------------------------------------------
# main() — error propagation
# ---------------------------------------------------------------------------

class TestMainErrors:
    def test_pipeline_error_propagates(self):
        with patch(PATCH_RECIPIENT, "pulse@example.com"), \
             patch(PATCH_RUN_PIPELINE, side_effect=RuntimeError("Groq is down")):
            with pytest.raises(RuntimeError, match="Groq is down"):
                run_module.main()

    def test_send_error_propagates(self):
        with patch(PATCH_RECIPIENT, "pulse@example.com"), \
             patch(PATCH_RUN_PIPELINE, return_value=_make_pipeline_result()), \
             patch(PATCH_COMPOSE, return_value=MagicMock()), \
             patch(PATCH_SEND_EMAIL, side_effect=Exception("SMTP failed")), \
             patch("scheduler.run.os.getenv", return_value="sender@gmail.com"):
            with pytest.raises(Exception, match="SMTP failed"):
                run_module.main()


# ---------------------------------------------------------------------------
# config defaults
# ---------------------------------------------------------------------------

class TestConfig:
    def test_default_weeks(self, monkeypatch):
        monkeypatch.delenv("SCHEDULER_WEEKS", raising=False)
        import scheduler.config as cfg
        import importlib
        importlib.reload(cfg)
        assert cfg.SCHEDULER_WEEKS == 3

    def test_default_max_reviews(self, monkeypatch):
        monkeypatch.delenv("SCHEDULER_MAX_REVIEWS", raising=False)
        import scheduler.config as cfg
        import importlib
        importlib.reload(cfg)
        assert cfg.SCHEDULER_MAX_REVIEWS == 200

    def test_weeks_overridable(self, monkeypatch):
        monkeypatch.setenv("SCHEDULER_WEEKS", "5")
        import scheduler.config as cfg
        import importlib
        importlib.reload(cfg)
        assert cfg.SCHEDULER_WEEKS == 5

    def test_max_reviews_overridable(self, monkeypatch):
        monkeypatch.setenv("SCHEDULER_MAX_REVIEWS", "500")
        import scheduler.config as cfg
        import importlib
        importlib.reload(cfg)
        assert cfg.SCHEDULER_MAX_REVIEWS == 500

    def test_recipient_email_default_empty(self, monkeypatch):
        monkeypatch.delenv("SCHEDULER_RECIPIENT_EMAIL", raising=False)
        import scheduler.config as cfg
        import importlib
        importlib.reload(cfg)
        assert cfg.SCHEDULER_RECIPIENT_EMAIL == ""

    def test_recipient_name_default_empty(self, monkeypatch):
        monkeypatch.delenv("SCHEDULER_RECIPIENT_NAME", raising=False)
        import scheduler.config as cfg
        import importlib
        importlib.reload(cfg)
        assert cfg.SCHEDULER_RECIPIENT_NAME == ""
