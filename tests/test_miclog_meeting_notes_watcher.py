import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import miclog_meeting_notes_watcher as watcher


def local_datetime(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute).astimezone()


def event(start: datetime, end: datetime) -> dict:
    return {
        "id": "event-1",
        "summary": "Test Meeting",
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
    }


class MiclogMeetingNotesWatcherTest(unittest.TestCase):
    def write_transcript(self, path: Path) -> None:
        path.write_text(
            "\n".join(
                [
                    "# Test Meeting - 2026-06-25 09:00:00",
                    "[2026-06-25 08:50:00] too early",
                    "[2026-06-25 09:02:00] first useful line",
                    "[2026-06-25 09:10:00] second useful line",
                    "[2026-06-25 10:00:00] too late",
                ]
            )
            + "\n"
        )

    def test_directory_input_selects_matching_transcript_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            miclog_dir = Path(tmp) / "memory" / "miclog"
            miclog_dir.mkdir(parents=True)
            transcript = miclog_dir / "20260625-090000-transcript-test-meeting-abc123.md"
            self.write_transcript(transcript)
            (miclog_dir / "20260625-090000-summary-test-meeting-abc123.md").write_text(
                "[2026-06-25 09:05:00] should be ignored\n"
            )

            lines, lower, upper = watcher.miclog_excerpt_for_event(
                miclog_dir,
                event(
                    local_datetime(2026, 6, 25, 9, 0),
                    local_datetime(2026, 6, 25, 9, 12),
                ),
                local_datetime(2026, 6, 25, 9, 20),
                timedelta(minutes=5),
            )

            self.assertEqual(lower, local_datetime(2026, 6, 25, 8, 55))
            self.assertEqual(upper, local_datetime(2026, 6, 25, 9, 17))
            self.assertEqual([line[2] for line in lines], [
                "[2026-06-25 09:02:00] first useful line",
                "[2026-06-25 09:10:00] second useful line",
            ])
            self.assertEqual({line[3] for line in lines}, {transcript})

    def test_directory_input_without_transcript_files_has_no_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            miclog_dir = Path(tmp) / "memory" / "miclog"
            miclog_dir.mkdir(parents=True)
            (miclog_dir / "AGENTS.md").write_text("# Miclog Files\n")
            (miclog_dir / ".DS_Store").write_text("")

            self.assertEqual(watcher.miclog_source_paths(miclog_dir), [])

    def test_single_file_input_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "legacy-transcript.md"
            self.write_transcript(transcript)

            lines, _, _ = watcher.miclog_excerpt_for_event(
                transcript,
                event(
                    local_datetime(2026, 6, 25, 9, 0),
                    local_datetime(2026, 6, 25, 9, 12),
                ),
                local_datetime(2026, 6, 25, 9, 20),
                timedelta(minutes=5),
            )

            self.assertEqual(len(lines), 2)
            self.assertEqual({line[3] for line in lines}, {transcript})

    def test_prompt_lists_selected_directory_transcript_path(self) -> None:
        old_repo_root = watcher.REPO_ROOT
        try:
            with tempfile.TemporaryDirectory() as tmp:
                watcher.REPO_ROOT = Path(tmp)
                miclog_dir = watcher.REPO_ROOT / "memory" / "miclog"
                miclog_dir.mkdir(parents=True)
                transcript = miclog_dir / "20260625-090000-transcript-test-meeting-abc123.md"
                self.write_transcript(transcript)
                meeting = event(
                    local_datetime(2026, 6, 25, 9, 0),
                    local_datetime(2026, 6, 25, 9, 12),
                )
                lines, lower, upper = watcher.miclog_excerpt_for_event(
                    miclog_dir,
                    meeting,
                    local_datetime(2026, 6, 25, 9, 20),
                    timedelta(minutes=5),
                )

                prompt = watcher.build_prompt(
                    event=meeting,
                    miclog_lines=lines,
                    miclog_path=miclog_dir,
                    excerpt_lower=lower,
                    excerpt_upper=upper,
                    max_miclog_chars=60000,
                )

                self.assertIn(
                    "memory/miclog/20260625-090000-transcript-test-meeting-abc123.md",
                    prompt,
                )
                self.assertNotIn("memory/miclog.txt", prompt)
        finally:
            watcher.REPO_ROOT = old_repo_root


if __name__ == "__main__":
    unittest.main()
