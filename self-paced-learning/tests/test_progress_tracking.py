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


if __name__ == "__main__":
    unittest.main(verbosity=2)
