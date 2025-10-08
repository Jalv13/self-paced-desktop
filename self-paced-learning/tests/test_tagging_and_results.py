"""Tests for tagging system integrity and quiz results rendering."""

import os
import sys
import unittest
from contextlib import contextmanager
from unittest.mock import patch

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
    get_progress_service,
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
        cls.progress_service = get_progress_service()

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

    def test_results_page_deduplicates_identical_remedial_lessons(self):
        """Weak topics that map to the same lesson should only surface once."""

        client = self.app.test_client()
        with client.session_transaction() as session:
            session["quiz_analysis"] = {
                "score": {"correct": 1, "total": 5, "percentage": 20},
                "weak_tags": ["unknown-topic-1", "unknown-topic-2"],
                "feedback": "Multiple areas need review.",
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
        self.assertEqual(len(lesson_plans), 1, "Expected duplicate lessons to be filtered out")
        self.assertIn("unknown-topic-1", lesson_plans)

        analysis_context = context["ANALYSIS_RESULTS"]
        self.assertEqual(analysis_context.get("weak_topics"), ["unknown-topic-1"])

    def test_full_quiz_flow_zero_score_triggers_remedial_once(self):
        """Simulate a full quiz submission with zero correct answers."""

        client = self.app.test_client()

        # Ensure a clean session for the simulated learner journey
        with client.session_transaction() as session:
            session.clear()

        # Start an actual quiz to seed session state and questions
        quiz_response = client.get("/quiz/python/functions")
        self.assertEqual(quiz_response.status_code, 200)

        # Submit empty answers to mimic a 0% score scenario
        analyze_response = client.post("/analyze", json={"answers": {}})
        self.assertEqual(analyze_response.status_code, 200)

        payload = analyze_response.get_json()
        self.assertIsInstance(payload, dict)
        self.assertTrue(payload.get("success"))

        analysis = payload.get("analysis", {})
        self.assertIsInstance(analysis, dict)
        self.assertEqual(analysis.get("score", {}).get("percentage"), 0)

        weak_topics = analysis.get("weak_topics") or []
        self.assertGreater(len(weak_topics), 0, "Expected weak topics when every question is missed")

        lowered_topics = [topic.lower() for topic in weak_topics]
        self.assertEqual(len(lowered_topics), len(set(lowered_topics)), "Expected weak topics to be deduplicated")

        # Render the results page using the captured analysis for this flow
        with capture_templates(self.app) as templates:
            results_response = client.get("/results")

        self.assertEqual(results_response.status_code, 200)
        self.assertGreater(len(templates), 0)

        template, context = templates[0]
        self.assertEqual(template.name, "results.html")

        analysis_context = context["ANALYSIS_RESULTS"]
        self.assertEqual(analysis_context["score"]["percentage"], 0)
        self.assertTrue(context["show_remedial"], "A failing score should trigger remedial guidance")

        lesson_plans = context["LESSON_PLANS"]
        self.assertGreater(len(lesson_plans), 0)

        seen_lessons = set()
        for lesson in lesson_plans.values():
            identifier = lesson.get("id") or lesson.get("title") or ""
            key = f"{lesson.get('subject')}:{lesson.get('subtopic')}:{str(identifier).lower()}"
            self.assertNotIn(key, seen_lessons, "Duplicate remedial lessons should be filtered out")
            seen_lessons.add(key)

    def _resolve_expected_answer(self, question):
        question_type = (question.get("type") or "multiple_choice").strip().lower()
        if question_type == "multiple_choice":
            options = question.get("options", []) or []
            answer_index = question.get("answer_index")
            if answer_index is None:
                answer_index = question.get("correct_answer_index")
            if isinstance(answer_index, int) and 0 <= answer_index < len(options):
                return str(options[answer_index])
            return str(question.get("correct_answer", ""))
        if question_type in {"fill_in_the_blank", "fill_blank"}:
            correct = question.get("correct_answer")
            if isinstance(correct, list):
                return str(correct[0]) if correct else ""
            if correct:
                return str(correct)
            acceptable = question.get("acceptable_answers") or question.get("correct_answers")
            if isinstance(acceptable, list) and acceptable:
                return str(acceptable[0])
            return ""
        return str(
            question.get("correct_answer")
            or question.get("expected_answer")
            or question.get("expected_output")
            or ""
        )

    def test_remedial_quiz_resets_question_context(self):
        """Remedial quiz generation should refresh session question data."""

        client = self.app.test_client()

        with client.session_transaction() as session:
            session.clear()

        quiz_response = client.get("/quiz/python/functions")
        self.assertEqual(quiz_response.status_code, 200)

        analyze_response = client.post("/analyze", json={"answers": {}})
        self.assertEqual(analyze_response.status_code, 200)

        analysis_payload = analyze_response.get_json()
        self.assertTrue(analysis_payload.get("success"))
        weak_topics = analysis_payload.get("analysis", {}).get("weak_topics") or []
        self.assertGreater(len(weak_topics), 0, "Weak topics should be detected for remedial generation")

        custom_pool = []
        for idx in range(9):
            tag = weak_topics[idx % len(weak_topics)]
            custom_pool.append(
                {
                    "id": f"remedial-{idx}",
                    "question": f"Custom remedial question {idx + 1}",
                    "type": "multiple_choice",
                    "options": ["A", "B", "C", "D"],
                    "answer_index": idx % 4,
                    "tags": [tag],
                }
            )

        with patch.object(
            self.data_service,
            "get_question_pool_questions",
            return_value=custom_pool,
        ):
            remedial_response = client.get("/generate_remedial_quiz")

        self.assertEqual(remedial_response.status_code, 200)
        remedial_payload = remedial_response.get_json()
        self.assertTrue(remedial_payload.get("success"))

        stored_count = remedial_payload.get("stored_question_count")
        self.assertGreaterEqual(stored_count, 7)
        self.assertLessEqual(stored_count, len(custom_pool))

        with client.session_transaction() as session:
            remedial_key = self.progress_service.get_session_key(
                "python", "functions", "remedial_questions"
            )
            session_remedial = session.get(remedial_key)
            analysis_key = self.progress_service.get_session_key(
                "python", "functions", "questions_served_for_analysis"
            )
            analysis_questions = session.get(analysis_key)
            quiz_type_key = self.progress_service.get_session_key(
                "python", "functions", "current_quiz_type"
            )
            active_quiz_type = session.get(quiz_type_key)

        self.assertIsInstance(session_remedial, list)
        self.assertEqual(len(session_remedial), stored_count)
        self.assertIsInstance(analysis_questions, list)
        self.assertEqual(len(analysis_questions), stored_count)
        self.assertEqual(active_quiz_type, "remedial")

        remedial_ids = {
            str(item.get("id") or item.get("question")) for item in session_remedial
        }
        analysis_ids = {
            str(item.get("id") or item.get("question")) for item in analysis_questions
        }
        self.assertEqual(
            remedial_ids,
            analysis_ids,
            "Remedial quiz context should match stored question set",
        )

        answer_payload = {}
        for index, question in enumerate(analysis_questions):
            answer_payload[f"q{index}"] = self._resolve_expected_answer(question)

        remedial_analyze_response = client.post(
            "/analyze", json={"answers": answer_payload}
        )
        self.assertEqual(remedial_analyze_response.status_code, 200)

        remedial_analysis_payload = remedial_analyze_response.get_json()
        self.assertTrue(remedial_analysis_payload.get("success"))
        remedial_analysis = remedial_analysis_payload.get("analysis", {})

        score_block = remedial_analysis.get("score", {})
        self.assertEqual(score_block.get("total"), len(analysis_questions))
        self.assertEqual(score_block.get("correct"), len(analysis_questions))
        self.assertEqual(score_block.get("percentage"), 100)
        self.assertFalse(remedial_analysis.get("wrong_question_indices"))

        with client.session_transaction() as session:
            analysis_session_key = self.progress_service.get_session_key(
                "python", "functions", "analysis_results"
            )
            stored_analysis = session.get(analysis_session_key)
        self.assertIsNotNone(stored_analysis)
        self.assertEqual(
            stored_analysis.get("score", {}).get("percentage"),
            100,
            "Stored remedial analysis should reflect the latest attempt",
        )


if __name__ == "__main__":
    unittest.main()
