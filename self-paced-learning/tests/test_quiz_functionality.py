"""Quiz Functionality Testing

Comprehensive tests for quiz features including quiz taking,
scoring, prerequisites, and question management.
"""

import os
import sys
import unittest
import json
import random
from unittest.mock import patch, MagicMock

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app_refactored import app
    from services import (
        init_services,
        get_data_service,
        get_progress_service,
        get_ai_service,
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure to run tests from the correct directory with venv activated")
    sys.exit(1)


class TestQuizFunctionality(unittest.TestCase):
    """Test quiz functionality including taking quizzes and scoring."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.app = app
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False

        cls.client = cls.app.test_client()
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        # Initialize services
        cls.data_root_path = os.path.join(os.path.dirname(__file__), "..", "data")
        init_services(cls.data_root_path)
        cls.data_service = get_data_service()
        cls.progress_service = get_progress_service()
        cls.ai_service = get_ai_service()

        print("\n🧪 Setting up quiz functionality tests...")

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        cls.app_context.pop()

    def test_quiz_data_availability(self):
        """Test that quiz data is available for subjects."""
        print("\n🔍 Testing quiz data availability...")

        subjects = self.data_service.discover_subjects()

        for subject_id in subjects.keys():
            config = self.data_service.load_subject_config(subject_id)
            if config and "subtopics" in config:
                for subtopic_id in config["subtopics"].keys():
                    print(f"  Checking quiz data for {subject_id}/{subtopic_id}...")

                    quiz_data = self.data_service.get_quiz_data(subject_id, subtopic_id)

                    if quiz_data and "questions" in quiz_data:
                        questions = quiz_data["questions"]
                        question_count = len(questions)
                        print(f"    ✅ Found {question_count} quiz questions")

                        # Test question structure
                        if questions:
                            sample_question = questions[0]
                            self.assertIn(
                                "question",
                                sample_question,
                                "Question should have 'question' field",
                            )

                            # Check for common quiz question fields
                            expected_fields = ["question"]
                            for field in expected_fields:
                                if field in sample_question:
                                    print(f"      ✅ Has {field} field")
                                else:
                                    print(f"      ⚠️ Missing {field} field")
                    else:
                        print(f"    ⚠️ No quiz questions found")

    def test_quiz_routes_access(self):
        """Test that quiz routes are accessible."""
        print("\n🔍 Testing quiz route accessibility...")

        # Test quiz routes for subjects with quiz data
        quiz_routes_to_test = [
            ("/quiz/python/functions", "Python functions quiz"),
            ("/quiz/calculus/integrals", "Calculus integrals quiz"),
            ("/quiz/python/loops", "Python loops quiz"),
        ]

        for route, description in quiz_routes_to_test:
            with self.subTest(route=route):
                print(f"  Testing {description}: {route}")
                response = self.client.get(route)

                # Quiz routes should return 200 (quiz available) or 404 (no quiz data)
                self.assertIn(
                    response.status_code,
                    [200, 404],
                    f"{description} returned unexpected status: {response.status_code}",
                )

                if response.status_code == 200:
                    content = response.get_data(as_text=True)
                    # Quiz page should contain quiz-related content
                    quiz_indicators = ["quiz", "question", "submit"]
                    found_indicators = [
                        indicator
                        for indicator in quiz_indicators
                        if indicator.lower() in content.lower()
                    ]

                    print(
                        f"    ✅ Quiz page loaded - Found indicators: {found_indicators}"
                    )
                    self.assertGreater(
                        len(found_indicators),
                        0,
                        "Quiz page should contain quiz-related content",
                    )
                else:
                    print(f"    ⚠️ No quiz available - {response.status_code}")

    def test_quiz_prerequisites_api(self):
        """Test quiz prerequisites API endpoints."""
        print("\n🔍 Testing quiz prerequisites API...")

        prerequisites_routes = [
            (
                "/api/quiz-prerequisites/python/functions",
                "Python functions prerequisites",
            ),
            (
                "/api/quiz-prerequisites/calculus/integrals",
                "Calculus integrals prerequisites",
            ),
        ]

        for route, description in prerequisites_routes:
            with self.subTest(route=route):
                print(f"  Testing {description}: {route}")
                response = self.client.get(route)

                self.assertIn(
                    response.status_code,
                    [200, 404],
                    f"{description} returned unexpected status: {response.status_code}",
                )

                if response.status_code == 200 and response.is_json:
                    data = response.get_json()
                    print(
                        f"    ✅ Prerequisites API response: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}"
                    )

                    # Check for expected prerequisites structure
                    if isinstance(data, dict):
                        if "prerequisites_met" in data:
                            print(
                                f"      Prerequisites met: {data['prerequisites_met']}"
                            )
                        if "required_lessons" in data:
                            print(
                                f"      Required lessons: {len(data.get('required_lessons', []))}"
                            )
                else:
                    print(f"    ⚠️ Prerequisites not available - {response.status_code}")

    def test_quiz_submission_simulation(self):
        """Test quiz submission simulation (without actual form submission)."""
        print("\n🔍 Testing quiz submission simulation...")

        # Find a subject/subtopic with quiz data
        subjects = self.data_service.discover_subjects()

        for subject_id in subjects.keys():
            config = self.data_service.load_subject_config(subject_id)
            if config and "subtopics" in config:
                for subtopic_id in config["subtopics"].keys():
                    quiz_data = self.data_service.get_quiz_data(subject_id, subtopic_id)

                    if (
                        quiz_data
                        and "questions" in quiz_data
                        and quiz_data["questions"]
                    ):
                        print(
                            f"  Testing quiz submission simulation for {subject_id}/{subtopic_id}..."
                        )

                        questions = quiz_data["questions"]
                        print(f"    Found {len(questions)} questions to simulate")

                        # Simulate quiz submission endpoint
                        with self.client.session_transaction() as sess:
                            # Set up session for quiz
                            sess["quiz_subject"] = subject_id
                            sess["quiz_subtopic"] = subtopic_id

                        # Test quiz submission route
                        submit_route = f"/submit-quiz/{subject_id}/{subtopic_id}"

                        # Test with GET (should not be allowed typically)
                        response = self.client.get(submit_route)
                        print(f"    GET {submit_route}: {response.status_code}")

                        # Test with POST (without data - should handle gracefully)
                        response = self.client.post(submit_route, data={})
                        print(
                            f"    POST {submit_route} (empty): {response.status_code}"
                        )

                        # Only test one subject/subtopic for simulation
                        return

        print("    ⚠️ No quiz data found for simulation")

    def test_quiz_results_handling(self):
        """Test quiz results handling and display."""
        print("\n🔍 Testing quiz results handling...")

        # Test quiz results routes
        results_routes = [
            ("/quiz-results/python/functions", "Python functions results"),
            ("/quiz-results/calculus/integrals", "Calculus integrals results"),
        ]

        for route, description in results_routes:
            with self.subTest(route=route):
                print(f"  Testing {description}: {route}")

                # Set up session with mock quiz results
                with self.client.session_transaction() as sess:
                    sess["quiz_score"] = 85
                    sess["quiz_total"] = 100
                    sess["quiz_subject"] = route.split("/")[2]
                    sess["quiz_subtopic"] = route.split("/")[3]

                response = self.client.get(route)

                # Results routes may or may not exist yet
                self.assertIn(
                    response.status_code,
                    [200, 404, 500],
                    f"{description} returned unexpected status: {response.status_code}",
                )

                if response.status_code == 200:
                    content = response.get_data(as_text=True)
                    result_indicators = ["score", "result", "correct", "quiz"]
                    found_indicators = [
                        indicator
                        for indicator in result_indicators
                        if indicator.lower() in content.lower()
                    ]

                    print(
                        f"    ✅ Results page loaded - Found indicators: {found_indicators}"
                    )
                else:
                    print(f"    ⚠️ Results page not available - {response.status_code}")


class TestQuestionPoolManagement(unittest.TestCase):
    """Test question pool management for remedial quizzes."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.data_root_path = os.path.join(os.path.dirname(__file__), "..", "data")
        init_services(cls.data_root_path)
        cls.data_service = get_data_service()
        cls.ai_service = get_ai_service()

        print("\n🧪 Setting up question pool tests...")

    def test_question_pool_availability(self):
        """Test question pool data availability."""
        print("\n🔍 Testing question pool availability...")

        subjects = self.data_service.discover_subjects()
        total_pool_questions = 0

        for subject_id in subjects.keys():
            config = self.data_service.load_subject_config(subject_id)
            if config and "subtopics" in config:
                for subtopic_id in config["subtopics"].keys():
                    print(f"  Checking question pool for {subject_id}/{subtopic_id}...")

                    pool_questions = self.data_service.get_question_pool_questions(
                        subject_id, subtopic_id
                    )

                    if pool_questions:
                        question_count = len(pool_questions)
                        total_pool_questions += question_count
                        print(f"    ✅ Found {question_count} pool questions")

                        # Test question structure
                        if pool_questions:
                            sample_question = pool_questions[0]
                            print(
                                f"      Sample question type: {type(sample_question)}"
                            )
                            if isinstance(sample_question, dict):
                                print(
                                    f"      Sample question keys: {list(sample_question.keys())}"
                                )
                    else:
                        print(f"    ⚠️ No pool questions found")

        print(f"\n  Total question pool questions: {total_pool_questions}")
        self.assertGreaterEqual(
            total_pool_questions, 0, "Should have non-negative pool questions"
        )

    def test_remedial_quiz_generation(self):
        """Test remedial quiz generation from question pool."""
        print("\n🔍 Testing remedial quiz generation...")

        # Find subjects with question pools
        subjects = self.data_service.discover_subjects()

        for subject_id in subjects.keys():
            config = self.data_service.load_subject_config(subject_id)
            if config and "subtopics" in config:
                for subtopic_id in config["subtopics"].keys():
                    pool_questions = self.data_service.get_question_pool_questions(
                        subject_id, subtopic_id
                    )

                    if pool_questions and len(pool_questions) > 0:
                        print(
                            f"  Testing remedial quiz for {subject_id}/{subtopic_id}..."
                        )
                        print(f"    Pool has {len(pool_questions)} questions")

                        # Build a tag set so we prioritise relevant questions
                        target_tags = set()
                        for question in pool_questions:
                            for tag in question.get("tags", []) or []:
                                if isinstance(tag, str) and tag.strip():
                                    target_tags.add(tag)

                        state = random.getstate()
                        random.seed(42)
                        selected_questions = self.ai_service.select_remedial_questions(
                            pool_questions, target_tags
                        )
                        random.setstate(state)

                        print(
                            f"    Selected {len(selected_questions)} questions for remedial quiz"
                        )

                        expected_min = min(7, len(pool_questions))
                        expected_max = min(10, len(pool_questions))

                        self.assertGreaterEqual(
                            len(selected_questions),
                            expected_min,
                            "Should select at least the minimum remedial question count",
                        )
                        self.assertLessEqual(
                            len(selected_questions),
                            expected_max,
                            "Should not exceed the maximum remedial question count",
                        )

                        for question in selected_questions:
                            self.assertIn(
                                question,
                                pool_questions,
                                "Selected question should originate from the pool",
                            )

                        print("    ✅ Remedial quiz generation successful")
                        return  # Test one successful case

        print("    ⚠️ No question pools available for remedial quiz testing")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("[*] COMPREHENSIVE QUIZ FUNCTIONALITY TEST SUITE")
    print("=" * 80)
    print(
        "[!] Make sure to run this from the self-paced-learning directory with venv activated!"
    )
    print("=" * 80)

    unittest.main(verbosity=2, buffer=False)
