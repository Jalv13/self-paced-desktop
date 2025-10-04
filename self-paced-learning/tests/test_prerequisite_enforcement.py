"""Tests for subtopic prerequisite enforcement pathways."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_refactored import app  # noqa: E402
from services import init_services, get_data_service, get_progress_service  # noqa: E402
from services.progress_service import ProgressService  # noqa: E402


class TestSubtopicPrerequisiteEnforcement(unittest.TestCase):
    """Validate that prerequisite checks block and unblock access correctly."""

    @classmethod
    def setUpClass(cls):
        """Prepare a Flask test app and supporting services."""

        cls.app = app
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False

        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        data_root_path = os.path.join(os.path.dirname(__file__), "..", "data")
        init_services(data_root_path)
        cls.data_service = get_data_service()
        cls.progress_service = get_progress_service()

        subject_config = cls.data_service.load_subject_config("python") or {}
        arrays_config = subject_config.get("subtopics", {}).get("arrays", {})
        cls.arrays_prereqs = arrays_config.get("prerequisites", [])

        cls.prerequisite_content = {}
        for prereq_id in cls.arrays_prereqs:
            lesson_payload = cls.data_service.get_lesson_plans("python", prereq_id) or []
            lesson_ids = [
                lesson.get("id")
                for lesson in lesson_payload
                if isinstance(lesson, dict) and lesson.get("id")
            ]

            videos_payload = cls.data_service.get_video_data("python", prereq_id) or {}
            video_ids = []
            for video in videos_payload.get("videos", []) or []:
                video_id = None
                if isinstance(video, dict):
                    video_id = video.get("id")
                if video_id:
                    video_ids.append(video_id)

            cls.prerequisite_content[prereq_id] = {
                "lesson_ids": lesson_ids,
                "video_ids": video_ids,
            }

    @classmethod
    def tearDownClass(cls):
        """Tear down the Flask application context."""

        cls.app_context.pop()

    def setUp(self):
        """Create a fresh client for each test to isolate session state."""

        self.client = self.app.test_client()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _complete_prerequisites_for_service(self, progress_service: ProgressService) -> None:
        """Mark all prerequisite lessons and videos as complete for a service."""

        for prereq_id, content in self.prerequisite_content.items():
            for lesson_id in content.get("lesson_ids", []):
                progress_service.mark_lesson_complete("python", prereq_id, lesson_id)
            for video_id in content.get("video_ids", []):
                progress_service.mark_video_complete("python", prereq_id, video_id)

    def _seed_session_with_prerequisites(self, session) -> None:
        """Populate a Flask session with completion data for prerequisites."""

        for prereq_id, content in self.prerequisite_content.items():
            lesson_ids = content.get("lesson_ids", [])
            if lesson_ids:
                session[
                    self.progress_service.get_session_key(
                        "python", prereq_id, "completed_lessons"
                    )
                ] = lesson_ids

            video_ids = content.get("video_ids", [])
            if video_ids:
                session[
                    self.progress_service.get_session_key(
                        "python", prereq_id, "watched_videos"
                    )
                ] = video_ids

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_service_flags_missing_prerequisites(self):
        """Service layer should block access when prerequisites are incomplete."""

        progress_service = ProgressService()
        status = progress_service.check_subtopic_prerequisites("python", "arrays")

        self.assertTrue(status["has_prerequisites"])
        self.assertFalse(status["can_access_subtopic"])
        missing = status.get("missing_prerequisites", [])
        self.assertIn("Python Functions", missing)
        self.assertGreater(len(missing), 0)

    def test_service_reports_completion_after_progress(self):
        """Service layer should permit access once all prerequisites are complete."""

        progress_service = ProgressService()
        self._complete_prerequisites_for_service(progress_service)
        status = progress_service.check_subtopic_prerequisites("python", "arrays")

        self.assertTrue(status["has_prerequisites"])
        self.assertTrue(status["can_access_subtopic"])
        self.assertEqual(status.get("missing_prerequisites"), [])
        self.assertEqual(status.get("completed_prerequisites"), status.get("total_prerequisites"))

    def test_api_reflects_prerequisite_progress(self):
        """API endpoint should update based on stored session progress."""

        response = self.client.get("/api/subtopic-prerequisites/python/arrays")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertTrue(data["has_prerequisites"])
        self.assertFalse(data["can_access_subtopic"])
        self.assertIn("Python Functions", data.get("missing_prerequisites", []))

        with self.client.session_transaction() as session:
            self._seed_session_with_prerequisites(session)

        follow_up = self.client.get("/api/subtopic-prerequisites/python/arrays")
        self.assertEqual(follow_up.status_code, 200)
        updated = follow_up.get_json()

        self.assertTrue(updated["can_access_subtopic"])
        self.assertEqual(updated.get("missing_prerequisites"), [])
        self.assertEqual(updated.get("completed_prerequisites"), updated.get("total_prerequisites"))

    def test_prerequisite_page_blocks_and_redirects(self):
        """Prerequisite page should render when blocked and redirect once complete."""

        blocked_response = self.client.get("/subjects/python/arrays/prerequisites")
        self.assertEqual(blocked_response.status_code, 200)
        page = blocked_response.get_data(as_text=True)
        self.assertIn("Complete these prerequisites", page)
        self.assertIn("Python Functions", page)

        with self.client.session_transaction() as session:
            self._seed_session_with_prerequisites(session)

        allowed_response = self.client.get("/subjects/python/arrays/prerequisites")
        self.assertEqual(allowed_response.status_code, 302)
        self.assertIn("/subjects/python", allowed_response.location)


if __name__ == "__main__":  # pragma: no cover - convenience for direct execution
    unittest.main()
