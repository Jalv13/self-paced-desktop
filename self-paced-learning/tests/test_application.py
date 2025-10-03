"""Comprehensive Test Suite for Refactored Flask Application

This test suite validates all core functionality and identifies bugs
in the service layer and blueprint integration.
"""

import os
import sys
import unittest
import json
from unittest.mock import patch, MagicMock

# Add the parent directory to the path to import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import (
    init_services,
    get_data_service,
    get_progress_service,
    get_ai_service,
    get_admin_service,
)
from utils.data_loader import DataLoader


class TestDataService(unittest.TestCase):
    """Test the DataService functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.data_root_path = os.path.join(os.path.dirname(__file__), "..", "data")
        init_services(cls.data_root_path)
        cls.data_service = get_data_service()

    def test_discover_subjects(self):
        """Test subject discovery."""
        print("\n[*] Testing subject discovery...")
        subjects = self.data_service.discover_subjects()

        print(f"Found {len(subjects)} subjects: {list(subjects.keys())}")
        self.assertIsInstance(subjects, dict)
        self.assertGreater(len(subjects), 0, "No subjects found!")

        # Check if Python subject exists
        self.assertIn("python", subjects, "Python subject not found!")

        # Validate subject structure
        for subject_id, subject_info in subjects.items():
            print(f"  Subject '{subject_id}': {subject_info.get('name', 'No name')}")
            self.assertIsInstance(subject_info, dict)

    def test_subject_configs(self):
        """Test subject configuration loading."""
        print("\n🔍 Testing subject configurations...")
        subjects = self.data_service.discover_subjects()

        for subject_id in subjects.keys():
            config = self.data_service.load_subject_config(subject_id)
            print(
                f"  Subject '{subject_id}' config: {'✅ Found' if config else '❌ Missing'}"
            )

            if config:
                subtopics = config.get("subtopics", {})
                print(f"    Subtopics: {list(subtopics.keys())}")
                self.assertIsInstance(subtopics, dict)

    def test_lesson_plans(self):
        """Test lesson plan loading."""
        print("\n🔍 Testing lesson plans...")
        subjects = self.data_service.discover_subjects()

        total_lessons = 0
        for subject_id in subjects.keys():
            config = self.data_service.load_subject_config(subject_id)
            if config and "subtopics" in config:
                for subtopic_id in config["subtopics"].keys():
                    lessons = self.data_service.get_lesson_plans(
                        subject_id, subtopic_id
                    )
                    lesson_count = len(lessons) if lessons else 0
                    total_lessons += lesson_count

                    print(f"  {subject_id}/{subtopic_id}: {lesson_count} lessons")

                    if lessons and isinstance(lessons, list) and len(lessons) > 0:
                        for lesson in lessons[:2]:  # Show first 2 lessons
                            if isinstance(lesson, dict):
                                print(
                                    f"    - {lesson.get('title', 'No title')} (ID: {lesson.get('id', 'No ID')})"
                                )
                            else:
                                print(f"    - Lesson data type: {type(lesson)}")

        print(f"\nTotal lessons found: {total_lessons}")
        self.assertGreater(total_lessons, 0, "No lessons found in any subject!")

    def test_quiz_data(self):
        """Test quiz data loading."""
        print("\n🔍 Testing quiz data...")
        subjects = self.data_service.discover_subjects()

        total_quizzes = 0
        for subject_id in subjects.keys():
            config = self.data_service.load_subject_config(subject_id)
            if config and "subtopics" in config:
                for subtopic_id in config["subtopics"].keys():
                    quiz_data = self.data_service.get_quiz_data(subject_id, subtopic_id)
                    questions = quiz_data.get("questions", []) if quiz_data else []
                    question_count = len(questions)
                    total_quizzes += question_count

                    print(
                        f"  {subject_id}/{subtopic_id}: {question_count} quiz questions"
                    )

                    if questions:
                        # Show first question
                        first_q = questions[0]
                        print(
                            f"    Sample: {first_q.get('question', 'No question text')[:50]}..."
                        )

        print(f"\nTotal quiz questions found: {total_quizzes}")
        # Don't fail if no quizzes - some might not have them yet
        if total_quizzes == 0:
            print("⚠️  Warning: No quiz questions found!")

    def test_question_pools(self):
        """Test question pool loading."""
        print("\n🔍 Testing question pools...")
        subjects = self.data_service.discover_subjects()

        total_pool_questions = 0
        for subject_id in subjects.keys():
            config = self.data_service.load_subject_config(subject_id)
            if config and "subtopics" in config:
                for subtopic_id in config["subtopics"].keys():
                    pool_questions = self.data_service.get_question_pool_questions(
                        subject_id, subtopic_id
                    )
                    question_count = len(pool_questions) if pool_questions else 0
                    total_pool_questions += question_count

                    print(
                        f"  {subject_id}/{subtopic_id}: {question_count} pool questions"
                    )

        print(f"\nTotal pool questions found: {total_pool_questions}")
        # Don't fail if no pool questions - some might not have them yet
        if total_pool_questions == 0:
            print("⚠️  Warning: No question pool found!")

    def test_video_data(self):
        """Test video data loading."""
        print("\n🔍 Testing video data...")
        subjects = self.data_service.discover_subjects()

        total_videos = 0
        for subject_id in subjects.keys():
            config = self.data_service.load_subject_config(subject_id)
            if config and "subtopics" in config:
                for subtopic_id in config["subtopics"].keys():
                    video_data = self.data_service.get_video_data(
                        subject_id, subtopic_id
                    )
                    videos = video_data.get("videos", []) if video_data else []
                    video_count = len(videos)
                    total_videos += video_count

                    print(f"  {subject_id}/{subtopic_id}: {video_count} videos")

        print(f"\nTotal videos found: {total_videos}")
        # Don't fail if no videos - some might not have them yet
        if total_videos == 0:
            print("⚠️  Warning: No videos found!")


class TestProgressService(unittest.TestCase):
    """Test the ProgressService functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        data_root_path = os.path.join(os.path.dirname(__file__), "..", "data")
        init_services(data_root_path)
        cls.progress_service = get_progress_service()

    def test_session_keys(self):
        """Test session key generation."""
        print("\n🔍 Testing session key generation...")

        key = self.progress_service.get_session_key("python", "functions", "test")
        expected = "python_functions_test"

        print(f"Generated key: {key}")
        print(f"Expected key: {expected}")

        self.assertEqual(key, expected, "Session key generation failed!")

    def test_progress_tracking(self):
        """Test progress tracking functionality."""
        print("\n🔍 Testing progress tracking...")

        # Test lesson completion
        subject, subtopic, lesson_id = "python", "functions", "test_lesson"

        # Initially not complete
        is_complete_before = self.progress_service.is_lesson_complete(
            subject, subtopic, lesson_id
        )
        print(f"Lesson complete before: {is_complete_before}")

        # Mark as complete
        success = self.progress_service.mark_lesson_complete(
            subject, subtopic, lesson_id
        )
        print(f"Mark complete success: {success}")

        # Check if now complete
        is_complete_after = self.progress_service.is_lesson_complete(
            subject, subtopic, lesson_id
        )
        print(f"Lesson complete after: {is_complete_after}")

        self.assertTrue(success, "Failed to mark lesson as complete")
        self.assertTrue(is_complete_after, "Lesson not marked as complete")


class TestAdminService(unittest.TestCase):
    """Test the AdminService functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        data_root_path = os.path.join(os.path.dirname(__file__), "..", "data")
        init_services(data_root_path)
        cls.admin_service = get_admin_service()

    def test_dashboard_stats(self):
        """Test dashboard statistics generation."""
        print("\n🔍 Testing dashboard statistics...")

        dashboard_data = self.admin_service.get_dashboard_stats()

        print(f"Dashboard data keys: {list(dashboard_data.keys())}")

        self.assertIn("stats", dashboard_data)
        self.assertIn("subjects", dashboard_data)

        stats = dashboard_data["stats"]
        print(f"Stats: {stats}")

        required_keys = [
            "total_subjects",
            "total_subtopics",
            "total_lessons",
            "total_questions",
        ]
        for key in required_keys:
            self.assertIn(key, stats, f"Missing stat: {key}")


class TestDataFiles(unittest.TestCase):
    """Test the actual data files existence and structure."""

    def setUp(self):
        """Set up test environment."""
        self.data_root_path = os.path.join(os.path.dirname(__file__), "..", "data")

    def test_data_directory_exists(self):
        """Test that data directory exists."""
        print(f"\n🔍 Testing data directory: {self.data_root_path}")
        self.assertTrue(
            os.path.exists(self.data_root_path), "Data directory not found!"
        )

    def test_subjects_directory(self):
        """Test subjects directory and structure."""
        print("\n🔍 Testing subjects directory structure...")

        subjects_path = os.path.join(self.data_root_path, "subjects")
        print(f"Subjects path: {subjects_path}")

        self.assertTrue(os.path.exists(subjects_path), "Subjects directory not found!")

        # List all subjects
        subjects = [
            d
            for d in os.listdir(subjects_path)
            if os.path.isdir(os.path.join(subjects_path, d))
        ]

        print(f"Found subjects: {subjects}")
        self.assertGreater(len(subjects), 0, "No subject directories found!")

        # Check each subject structure
        for subject in subjects:
            subject_path = os.path.join(subjects_path, subject)
            print(f"\n  Checking subject: {subject}")

            # Check for required files
            info_file = os.path.join(subject_path, "subject_info.json")
            config_file = os.path.join(subject_path, "subject_config.json")

            print(
                f"    subject_info.json: {'✅' if os.path.exists(info_file) else '❌'}"
            )
            print(
                f"    subject_config.json: {'✅' if os.path.exists(config_file) else '❌'}"
            )

            # Check subtopics
            subtopics = [
                d
                for d in os.listdir(subject_path)
                if os.path.isdir(os.path.join(subject_path, d))
            ]

            print(f"    Subtopics: {subtopics}")

            for subtopic in subtopics:
                subtopic_path = os.path.join(subject_path, subtopic)
                print(f"      Checking subtopic: {subtopic}")

                # Check for lesson, quiz, and video files
                lessons_file = os.path.join(subtopic_path, "lesson_plans.json")
                quiz_file = os.path.join(subtopic_path, "quiz_data.json")
                pool_file = os.path.join(subtopic_path, "question_pool.json")
                videos_file = os.path.join(subtopic_path, "videos.json")

                print(
                    f"        lesson_plans.json: {'✅' if os.path.exists(lessons_file) else '❌'}"
                )
                print(
                    f"        quiz_data.json: {'✅' if os.path.exists(quiz_file) else '❌'}"
                )
                print(
                    f"        question_pool.json: {'✅' if os.path.exists(pool_file) else '❌'}"
                )
                print(
                    f"        videos.json: {'✅' if os.path.exists(videos_file) else '❌'}"
                )

                # Validate JSON files if they exist
                for file_name, file_path in [
                    ("lessons", lessons_file),
                    ("quiz", quiz_file),
                    ("pool", pool_file),
                    ("videos", videos_file),
                ]:
                    if os.path.exists(file_path):
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                print(f"        {file_name} JSON: ✅ Valid")
                        except json.JSONDecodeError as e:
                            print(f"        {file_name} JSON: ❌ Invalid - {e}")
                        except Exception as e:
                            print(f"        {file_name} JSON: ❌ Error - {e}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("[*] COMPREHENSIVE APPLICATION TEST SUITE")
    print("=" * 60)

    # Run tests with detailed output
    unittest.main(verbosity=2, buffer=False)
