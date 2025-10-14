"""Progress tracking integration tests."""

import json
import os
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(PROJECT_ROOT))

from app_refactored import app  # noqa: E402
from services import get_progress_service  # noqa: E402


DATA_SUBJECTS_ROOT = PROJECT_ROOT / "data" / "subjects"


class TestProgressTracking(unittest.TestCase):
    """Verify that progress endpoints unlock quizzes when content is opened."""

    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.app.config["TESTING"] = True
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        cls.progress_service = get_progress_service()

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    def setUp(self):
        self.app = self.__class__.app
        self.client = self.app.test_client()
        self.progress_service = self.__class__.progress_service
        # Ensure a clean slate for each test run
        with self.app.test_request_context():
            self.progress_service.clear_all_session_data()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _load_content_identifiers(self, subject: str, subtopic: str):
        """Load lesson and video identifiers used for progress tracking."""

        lesson_payload_path = (
            DATA_SUBJECTS_ROOT / subject / subtopic / "lesson_plans.json"
        )
        with lesson_payload_path.open("r", encoding="utf-8") as handle:
            lesson_payload = json.load(handle)

        lesson_ids = [
            lesson.get("id")
            for lesson in lesson_payload.get("lessons", [])
            if isinstance(lesson, dict) and lesson.get("id")
        ]

        video_payload_path = (
            DATA_SUBJECTS_ROOT / subject / subtopic / "videos.json"
        )
        with video_payload_path.open("r", encoding="utf-8") as handle:
            video_payload = json.load(handle)

        videos_node = video_payload.get("videos", {})
        if isinstance(videos_node, dict):
            video_ids = list(videos_node.keys())
        else:
            video_ids = [
                video.get("id") or video.get("video_id")
                for video in videos_node
                if isinstance(video, dict)
            ]

        self.assertGreater(len(lesson_ids), 0, "Expected lesson IDs for test subject")
        self.assertGreater(len(video_ids), 0, "Expected video IDs for test subject")

        return lesson_ids, video_ids

    def _split_lessons_by_type(self, subject: str, subtopic: str):
        """Return lesson identifiers grouped by declared type."""

        lesson_payload_path = (
            DATA_SUBJECTS_ROOT / subject / subtopic / "lesson_plans.json"
        )
        with lesson_payload_path.open("r", encoding="utf-8") as handle:
            lesson_payload = json.load(handle)

        raw_lessons = lesson_payload.get("lessons", [])
        items = []
        if isinstance(raw_lessons, dict):
            items = [(lesson_id, lesson or {}) for lesson_id, lesson in raw_lessons.items()]
        elif isinstance(raw_lessons, list):
            for index, lesson in enumerate(raw_lessons):
                lesson = lesson or {}
                lesson_id = lesson.get("id") or f"lesson_{index + 1}"
                items.append((lesson_id, lesson))

        initial_like: list[str] = []
        remedial_like: list[str] = []
        other: list[str] = []

        for lesson_id, lesson in items:
            raw_type = lesson.get("type")
            normalized = "" if raw_type is None else str(raw_type).strip().lower()

            if normalized in {"", "initial", "all"}:
                initial_like.append(lesson_id)
            elif normalized == "remedial":
                remedial_like.append(lesson_id)
            else:
                other.append(lesson_id)

        return initial_like, remedial_like, other

    def test_opening_lesson_and_video_unlocks_quiz(self):
        """Posting progress for a lesson and video should satisfy prerequisites."""

        subject = "python"
        subtopic = "functions"
        lesson_ids, video_ids = self._load_content_identifiers(subject, subtopic)

        with self.client as client:
            initial_response = client.get(
                f"/api/quiz-prerequisites/{subject}/{subtopic}"
            )
            self.assertEqual(initial_response.status_code, 200)
            initial = initial_response.get_json()

            self.assertFalse(initial.get("lessons_complete"))
            self.assertFalse(initial.get("videos_complete"))

            for lesson_id in lesson_ids:
                lesson_update = client.post(
                    "/api/progress/update",
                    json={
                        "subject": subject,
                        "subtopic": subtopic,
                        "item_id": lesson_id,
                        "item_type": "lesson",
                    },
                )
                self.assertEqual(lesson_update.status_code, 200)
                self.assertTrue(lesson_update.is_json)
                self.assertTrue(lesson_update.get_json().get("success"))

            for video_id in video_ids:
                video_update = client.post(
                    "/api/progress/update",
                    json={
                        "subject": subject,
                        "subtopic": subtopic,
                        "item_id": video_id,
                        "item_type": "video",
                    },
                )
                self.assertEqual(video_update.status_code, 200)
                self.assertTrue(video_update.is_json)
                self.assertTrue(video_update.get_json().get("success"))

            final_response = client.get(
                f"/api/quiz-prerequisites/{subject}/{subtopic}"
            )
            self.assertEqual(final_response.status_code, 200)
            final = final_response.get_json()

            self.assertTrue(final.get("lessons_complete"))
            self.assertTrue(final.get("videos_complete"))
            self.assertTrue(final.get("all_met"))

    def test_progress_persists_across_refresh_and_reopen(self):
        """Progress should remain complete after refresh and redundant posts."""

        subject = "python"
        subtopic = "functions"
        lesson_ids, video_ids = self._load_content_identifiers(subject, subtopic)

        with self.client as client:
            baseline_response = client.get(
                f"/api/progress/check/{subject}/{subtopic}"
            )
            self.assertEqual(baseline_response.status_code, 200)
            baseline = baseline_response.get_json()

            self.assertEqual(baseline["lessons"]["completed_count"], 0)
            self.assertEqual(baseline["videos"]["watched_count"], 0)
            self.assertFalse(baseline["overall"]["is_complete"])

            for lesson_id in lesson_ids:
                response = client.post(
                    "/api/progress/update",
                    json={
                        "subject": subject,
                        "subtopic": subtopic,
                        "item_id": lesson_id,
                        "item_type": "lesson",
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.is_json)
                self.assertTrue(response.get_json().get("success"))

            for video_id in video_ids:
                response = client.post(
                    "/api/progress/update",
                    json={
                        "subject": subject,
                        "subtopic": subtopic,
                        "item_id": video_id,
                        "item_type": "video",
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.is_json)
                self.assertTrue(response.get_json().get("success"))

            after_first_response = client.get(
                f"/api/progress/check/{subject}/{subtopic}"
            )
            after_first = after_first_response.get_json()

            self.assertEqual(
                after_first["lessons"]["completed_count"], len(lesson_ids)
            )
            self.assertEqual(
                after_first["videos"]["watched_count"], len(video_ids)
            )
            self.assertTrue(after_first["overall"]["is_complete"])
            self.assertGreaterEqual(after_first["overall"]["completion_percentage"], 100)

            # Repost the same completions to mimic reopening lessons/videos
            for lesson_id in lesson_ids:
                response = client.post(
                    "/api/progress/update",
                    json={
                        "subject": subject,
                        "subtopic": subtopic,
                        "item_id": lesson_id,
                        "item_type": "lesson",
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.get_json().get("success"))

            for video_id in video_ids:
                response = client.post(
                    "/api/progress/update",
                    json={
                        "subject": subject,
                        "subtopic": subtopic,
                        "item_id": video_id,
                        "item_type": "video",
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.get_json().get("success"))

            after_repeat_response = client.get(
                f"/api/progress/check/{subject}/{subtopic}"
            )
            after_repeat = after_repeat_response.get_json()

            self.assertEqual(
                after_repeat["lessons"]["completed_count"], len(lesson_ids)
            )
            self.assertEqual(
                after_repeat["videos"]["watched_count"], len(video_ids)
            )
            self.assertTrue(after_repeat["overall"]["is_complete"])
            self.assertGreaterEqual(
                after_repeat["overall"]["completion_percentage"], 100
            )

            quiz_state = client.get(
                f"/api/quiz-prerequisites/{subject}/{subtopic}"
            ).get_json()
            self.assertTrue(quiz_state.get("lessons_complete"))
            self.assertTrue(quiz_state.get("videos_complete"))
            self.assertTrue(quiz_state.get("all_met"))

    def test_only_initial_lessons_required_when_no_videos_present(self):
        """Ensure remedial lessons do not gate the initial quiz."""

        subject = "python"
        subtopic = "week_1"
        initial_lessons, remedial_lessons, other_lessons = self._split_lessons_by_type(
            subject, subtopic
        )

        # Sanity checks to ensure the fixture exercises the right scenario
        self.assertGreater(len(initial_lessons), 0)
        self.assertGreater(len(remedial_lessons), 0)
        self.assertEqual(other_lessons, [])

        with self.client as client:
            baseline_response = client.get(
                f"/api/quiz-prerequisites/{subject}/{subtopic}"
            )
            self.assertEqual(baseline_response.status_code, 200)
            baseline = baseline_response.get_json()

            self.assertEqual(baseline["lesson_total"], len(initial_lessons))
            self.assertFalse(baseline["lessons_complete"])
            self.assertEqual(baseline["videos_total"], 0)
            self.assertTrue(baseline["videos_complete"])

            for lesson_id in initial_lessons:
                update = client.post(
                    "/api/progress/update",
                    json={
                        "subject": subject,
                        "subtopic": subtopic,
                        "item_id": lesson_id,
                        "item_type": "lesson",
                    },
                )
                self.assertEqual(update.status_code, 200)
                self.assertTrue(update.get_json().get("success"))

            follow_up_response = client.get(
                f"/api/quiz-prerequisites/{subject}/{subtopic}"
            )
            self.assertEqual(follow_up_response.status_code, 200)
            follow_up = follow_up_response.get_json()

            self.assertEqual(follow_up["lesson_total"], len(initial_lessons))
            self.assertEqual(
                follow_up["lessons_completed"], len(initial_lessons)
            )
            self.assertTrue(follow_up["lessons_complete"])
            self.assertEqual(follow_up["videos_total"], 0)
            self.assertTrue(follow_up["videos_complete"])
            self.assertTrue(follow_up["all_met"])
            self.assertTrue(follow_up["can_take_quiz"])
            self.assertEqual(follow_up.get("missing_lessons"), [])
            self.assertEqual(follow_up.get("missing_items"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
