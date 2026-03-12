"""
Phase 3 — Note Assembler (no LLM).

Combines ThemeSummary × 3 + action ideas into a fixed Markdown template
and writes output/weekly_pulse.md.
"""

from pathlib import Path

from phase3.models import PulseNote

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
PULSE_MD_PATH = OUTPUT_DIR / "weekly_pulse.md"

_TEMPLATE = """\
Weekly App Review Pulse — {week_label}
─────────────────────────────────────────

TOP THEMES
{top_themes_block}

USER VOICES
{user_voices_block}

WHAT'S WORKING
{whats_working_block}

ACTION IDEAS
{action_ideas_block}
"""


def assemble(note: PulseNote, output_path: Path | None = None) -> str:
    """
    Render a PulseNote as Markdown and write to output/weekly_pulse.md.

    Args:
        note:        fully populated PulseNote from note_generator.generate_pulse()
        output_path: override the output file path (used in tests)

    Returns:
        The rendered Markdown string (also written to disk).
    """
    # TOP THEMES block
    top_themes_lines = []
    for i, ts in enumerate(note.theme_summaries, 1):
        top_themes_lines.append(f"  {i}. {ts.label} — {ts.summary}")
    top_themes_block = "\n".join(top_themes_lines)

    # USER VOICES block
    voices_lines = []
    for ts in note.theme_summaries:
        voices_lines.append(
            f'  "{ts.representative_quote}"'
            f"  — {ts.quote_platform}, {ts.quote_rating}★"
        )
    user_voices_block = "\n".join(voices_lines)

    # WHAT'S WORKING block
    working_lines = []
    for i, item in enumerate(note.whats_working, 1):
        working_lines.append(f"  {i}. {item}")
    whats_working_block = "\n".join(working_lines)

    # ACTION IDEAS block
    action_lines = []
    for i, idea in enumerate(note.action_ideas, 1):
        action_lines.append(f"  {i}. {idea}")
    action_ideas_block = "\n".join(action_lines)

    markdown = _TEMPLATE.format(
        week_label=note.week_label,
        top_themes_block=top_themes_block,
        user_voices_block=user_voices_block,
        whats_working_block=whats_working_block,
        action_ideas_block=action_ideas_block,
    )

    path = output_path or PULSE_MD_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")

    return markdown
