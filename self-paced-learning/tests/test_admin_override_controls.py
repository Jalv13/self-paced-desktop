import os
import sys
import unittest
from flask import render_template

# Ensure the application modules are importable when pytest adjusts sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_refactored import app
from services import get_progress_service


class TestAdminOverrideControls(unittest.TestCase):
    """Validate admin override toggling and prerequisite enforcement."""

    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.client = cls.app.test_client()
        cls.progress_service = get_progress_service()

    def setUp(self):
        # Ensure a clean session for each test run
        with self.client.session_transaction() as sess:
            sess.clear()

    def test_toggle_override_endpoint(self):
        """POST /admin/toggle-override should enable and disable override explicitly."""
        # Initial status should be disabled
        response = self.client.get("/admin/toggle-override")
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertFalse(data["admin_override"])

        # Enable override via POST toggle
        enable_response = self.client.post("/admin/toggle-override")
        enable_data = enable_response.get_json()
        self.assertTrue(enable_data["success"])
        self.assertTrue(enable_data["admin_override"])

        # API status endpoint should reflect enabled override
        status_response = self.client.get("/api/admin/status")
        status_data = status_response.get_json()
        self.assertTrue(status_data["success"])
        self.assertTrue(status_data["admin_override"])

        # Explicitly disable override
        disable_response = self.client.post(
            "/admin/toggle-override", json={"enabled": False}
        )
        disable_data = disable_response.get_json()
        self.assertTrue(disable_data["success"])
        self.assertFalse(disable_data["admin_override"])

        with self.client.session_transaction() as sess:
            self.assertFalse(sess.get("admin_override", False))

    def test_prerequisites_respected_when_override_off(self):
        """Prerequisites should block quiz access when override is disabled."""
        with self.app.test_request_context():
            self.progress_service.clear_all_session_data()
            self.progress_service.set_admin_override(False)
            prerequisites = self.progress_service.check_quiz_prerequisites(
                "python", "functions"
            )

            # Ensure prerequisites exist and are enforced
            self.assertTrue(prerequisites["has_prerequisites"])
            self.assertFalse(prerequisites["can_take_quiz"])

            # Enabling override should bypass the gate
            self.progress_service.set_admin_override(True)
            bypassed = self.progress_service.check_quiz_prerequisites(
                "python", "functions"
            )
            self.assertTrue(bypassed["can_take_quiz"])

    def test_results_template_hides_admin_controls_when_disabled(self):
        """Results page should only render admin controls while override is active."""
        base_payload = {
            "analysis": {"score": {"correct": 0, "total": 0, "percentage": 0}},
            "ANALYSIS_RESULTS": {"score": {"correct": 0, "total": 0, "percentage": 0}},
            "answers": [],
            "subject": "python",
            "subtopic": "functions",
            "CURRENT_SUBJECT": "python",
            "CURRENT_SUBTOPIC": "functions",
            "LESSON_PLANS": {},
            "VIDEO_DATA": {},
            "video_recommendations": [],
            "show_remedial": False,
            "quiz_generation_error": None,
        }

        with self.app.test_request_context():
            html_disabled = render_template(
                "results.html",
                **base_payload,
                admin_override=False,
                is_admin=False,
            )

        self.assertNotIn("Admin Override Active", html_disabled)
        self.assertNotIn("Admin: Mark All Complete", html_disabled)

        with self.app.test_request_context():
            html_enabled = render_template(
                "results.html",
                **base_payload,
                admin_override=True,
                is_admin=True,
            )

        self.assertIn("Admin Override Active", html_enabled)
        self.assertIn("Admin: Mark All Complete", html_enabled)
        self.assertNotIn("Disable Override", html_enabled)


if __name__ == "__main__":
    unittest.main()
