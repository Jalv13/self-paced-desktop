"""Tests for tagging system integrity and quiz results rendering."""

import os
import sys
import unittest
from contextlib import contextmanager

from flask import template_rendered


# Ensure application package is importable
TEST_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


from app_refactored import app  # noqa: E402
from services import (  # noqa: E402
    get_ai_service,
    get_data_service,
    init_services,
)


@contextmanager
def capture_templates(flask_app):
    """Capture templates rendered within a Flask context."""

    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, flask_app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, flask_app)


class TestTaggingAndResults(unittest.TestCase):
    """Validate tagging system utilities and quiz results rendering."""

    @classmethod
    def setUpClass(cls):
        cls.app = app
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False

        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        data_root_path = os.path.join(PROJECT_ROOT, "data")
        init_services(data_root_path)
        cls.data_service = get_data_service()
        cls.ai_service = get_ai_service()

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    def test_allowed_tags_are_normalized_strings(self):
        """Allowed tags should be strings with whitespace trimmed and lower-casing applied."""

        tags = self.data_service.get_subject_allowed_tags("python")

        self.assertIsInstance(tags, list)
        self.assertGreater(len(tags), 0, "Expected allowed tags for python subject")
        for tag in tags:
            self.assertIsInstance(tag, str)
            self.assertEqual(tag, tag.strip())
            self.assertEqual(tag, tag.lower())

        # Ensure duplicates are removed when normalized
        normalized = {tag.lower() for tag in tags}
        self.assertEqual(len(normalized), len(tags))

    def test_find_lessons_by_tags_matches_expected_content(self):
        """Tag search should surface lessons that contain all requested tags."""

        matching = self.data_service.find_lessons_by_tags("python", ["functions"])

        self.assertGreater(len(matching), 0, "Expected at least one lesson tagged with 'functions'")
        for lesson in matching:
            self.assertIn("functions", lesson.get("tags", []))
            self.assertEqual(lesson.get("subject"), "python")

    def test_analyze_quiz_performance_tracks_allowed_tags(self):
        """Quiz analysis should surface weak tags drawn from the allowed tag list."""

        quiz_payload = self.data_service.get_quiz_data("python", "functions")
        questions = quiz_payload.get("questions", [])[:3]
        self.assertGreater(len(questions), 0, "Sample quiz questions are required for analysis tests")

        # Provide empty answers so every question is marked incorrect
        answers = [""] * len(questions)

        analysis = self.ai_service.analyze_quiz_performance(
            questions,
            answers,
            "python",
            "functions",
        )

        allowed = set(self.data_service.get_subject_allowed_tags("python"))
        weak_tags = analysis.get("weak_tags", [])

        self.assertEqual(analysis["score"]["correct"], 0)
        self.assertEqual(analysis["score"]["total"], len(questions))
        self.assertLess(analysis["score"]["percentage"], 1)
        self.assertGreater(len(weak_tags), 0, "Expected weak tags when every question is incorrect")
        self.assertTrue(set(weak_tags).issubset(allowed))
        self.assertEqual(weak_tags, analysis.get("weak_topics"))
        self.assertTrue(analysis.get("feedback"))

    def test_results_page_renders_with_analysis_context(self):
        """The results view should surface lesson plans and analysis metadata."""

        client = self.app.test_client()
        with client.session_transaction() as session:
            session["quiz_analysis"] = {
                "score": {"correct": 2, "total": 5, "percentage": 40},
                "weak_tags": ["functions"],
                "feedback": "Focus on reviewing function fundamentals.",
                "recommendations": ["Review the remedial lesson."]
            }
            session["quiz_answers"] = ["A", "B", "C"]
            session["current_subject"] = "python"
            session["current_subtopic"] = "functions"

        with capture_templates(self.app) as templates:
            response = client.get("/results")

        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(templates), 0)

        template, context = templates[0]
        self.assertEqual(template.name, "results.html")

        lesson_plans = context["LESSON_PLANS"]
        self.assertIn("functions", lesson_plans)
        lesson_entry = lesson_plans["functions"]
        self.assertEqual(lesson_entry.get("subject"), "python")
        self.assertEqual(lesson_entry.get("subtopic"), "functions")

        analysis_context = context["ANALYSIS_RESULTS"]
        self.assertEqual(analysis_context["score"]["percentage"], 40)
        self.assertTrue(context["show_remedial"])


if __name__ == "__main__":
    unittest.main()
