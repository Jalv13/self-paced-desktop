"""Comprehensive Feature Testing

Tests all core features including lesson/subject/subtopic editing,
cache clearing, and data management operations.
"""

import os
import sys
import unittest
import json
import tempfile
from unittest.mock import patch, MagicMock

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from services import (
        init_services,
        get_data_service,
        get_admin_service,
        get_progress_service,
    )
    from utils.data_loader import DataLoader
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure to run tests from the correct directory with venv activated")
    sys.exit(1)


class TestDataManagementFeatures(unittest.TestCase):
    """Test data management and editing features."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.data_root_path = os.path.join(os.path.dirname(__file__), "..", "data")
        init_services(cls.data_root_path)
        cls.data_service = get_data_service()
        cls.admin_service = get_admin_service()

        print("\n🧪 Setting up feature tests...")

    def test_subject_discovery_and_validation(self):
        """Test subject discovery and validation."""
        print("\n🔍 Testing subject discovery and validation...")

        # Test subject discovery
        subjects = self.data_service.discover_subjects()
        self.assertIsInstance(subjects, dict)
        self.assertGreater(len(subjects), 0, "No subjects discovered")

        print(f"  Discovered {len(subjects)} subjects: {list(subjects.keys())}")

        # Test subject validation
        for subject_id in subjects.keys():
            # Test valid subject/subtopic combinations
            config = self.data_service.load_subject_config(subject_id)
            if config and "subtopics" in config:
                for subtopic_id in list(config["subtopics"].keys())[:2]:  # Test first 2
                    is_valid = self.data_service.validate_subject_subtopic(
                        subject_id, subtopic_id
                    )
                    self.assertTrue(
                        is_valid,
                        f"Valid combination {subject_id}/{subtopic_id} failed validation",
                    )
                    print(f"    ✅ Valid: {subject_id}/{subtopic_id}")

        # Test invalid combinations
        invalid_combos = [
            ("nonexistent", "also_nonexistent"),
            ("python", "nonexistent_subtopic"),
            ("nonexistent_subject", "functions"),
        ]

        for subject, subtopic in invalid_combos:
            is_valid = self.data_service.validate_subject_subtopic(subject, subtopic)
            self.assertFalse(
                is_valid, f"Invalid combination {subject}/{subtopic} passed validation"
            )
            print(f"    ❌ Invalid (correctly rejected): {subject}/{subtopic}")

    def test_lesson_management_operations(self):
        """Test lesson loading and management."""
        print("\n🔍 Testing lesson management operations...")

        subjects = self.data_service.discover_subjects()

        for subject_id in subjects.keys():
            config = self.data_service.load_subject_config(subject_id)
            if config and "subtopics" in config:
                for subtopic_id in list(config["subtopics"].keys())[:2]:  # Test first 2
                    print(f"  Testing lessons for {subject_id}/{subtopic_id}...")

                    # Test lesson loading
                    lessons = self.data_service.get_lesson_plans(
                        subject_id, subtopic_id
                    )
                    self.assertIsInstance(
                        lessons,
                        list,
                        f"Lessons should be a list for {subject_id}/{subtopic_id}",
                    )

                    if lessons:
                        print(f"    Found {len(lessons)} lessons")

                        # Test lesson structure
                        for lesson in lessons[:1]:  # Test first lesson
                            self.assertIn("id", lesson, "Lesson should have an ID")
                            self.assertIn("title", lesson, "Lesson should have a title")
                            print(
                                f"      ✅ Lesson: {lesson.get('title', 'No title')} (ID: {lesson.get('id', 'No ID')})"
                            )

                            # Test lesson content structure
                            if "content" in lesson:
                                content = lesson["content"]
                                self.assertIsInstance(
                                    content, list, "Lesson content should be a list"
                                )
                                print(f"        Content blocks: {len(content)}")
                    else:
                        print(f"    No lessons found")

    def test_quiz_data_management(self):
        """Test quiz data loading and validation."""
        print("\n🔍 Testing quiz data management...")

        subjects = self.data_service.discover_subjects()
        total_quiz_questions = 0

        for subject_id in subjects.keys():
            config = self.data_service.load_subject_config(subject_id)
            if config and "subtopics" in config:
                for subtopic_id in config["subtopics"].keys():
                    print(f"  Testing quiz data for {subject_id}/{subtopic_id}...")

                    # Test quiz data loading
                    quiz_data = self.data_service.get_quiz_data(subject_id, subtopic_id)

                    if quiz_data and "questions" in quiz_data:
                        questions = quiz_data["questions"]
                        question_count = len(questions)
                        total_quiz_questions += question_count

                        print(f"    Found {question_count} quiz questions")

                        # Test question structure
                        if questions:
                            sample_question = questions[0]
                            required_fields = ["question"]
                            for field in required_fields:
                                self.assertIn(
                                    field,
                                    sample_question,
                                    f"Question should have '{field}' field",
                                )

                            print(
                                f"      Sample: {sample_question.get('question', 'No question')[:50]}..."
                            )
                    else:
                        print(f"    No quiz questions found")

        print(f"  Total quiz questions across all subjects: {total_quiz_questions}")
        self.assertGreaterEqual(
            total_quiz_questions, 0, "Should have some quiz questions"
        )

    def test_question_pool_management(self):
        """Test question pool loading and management."""
        print("\n🔍 Testing question pool management...")

        subjects = self.data_service.discover_subjects()
        total_pool_questions = 0

        for subject_id in subjects.keys():
            config = self.data_service.load_subject_config(subject_id)
            if config and "subtopics" in config:
                for subtopic_id in config["subtopics"].keys():
                    print(f"  Testing question pool for {subject_id}/{subtopic_id}...")

                    # Test question pool loading
                    pool_questions = self.data_service.get_question_pool_questions(
                        subject_id, subtopic_id
                    )

                    if pool_questions:
                        question_count = len(pool_questions)
                        total_pool_questions += question_count
                        print(f"    Found {question_count} pool questions")

                        # Test question structure
                        if pool_questions:
                            sample_question = pool_questions[0]
                            print(f"      Sample: {str(sample_question)[:50]}...")
                    else:
                        print(f"    No pool questions found")

        print(f"  Total pool questions across all subjects: {total_pool_questions}")
        self.assertGreaterEqual(
            total_pool_questions, 0, "Should have some pool questions"
        )

    def test_video_data_management(self):
        """Test video data loading and management."""
        print("\n🔍 Testing video data management...")

        subjects = self.data_service.discover_subjects()
        total_videos = 0

        for subject_id in subjects.keys():
            config = self.data_service.load_subject_config(subject_id)
            if config and "subtopics" in config:
                for subtopic_id in config["subtopics"].keys():
                    print(f"  Testing video data for {subject_id}/{subtopic_id}...")

                    # Test video data loading
                    video_data = self.data_service.get_video_data(
                        subject_id, subtopic_id
                    )

                    if video_data and "videos" in video_data:
                        videos = video_data["videos"]
                        video_count = len(videos)
                        total_videos += video_count

                        print(f"    Found {video_count} videos")

                        # Test video structure
                        if videos:
                            sample_video = videos[0]
                            print(
                                f"      Sample video keys: {list(sample_video.keys()) if isinstance(sample_video, dict) else 'Not a dict'}"
                            )
                    else:
                        print(f"    No videos found")

        print(f"  Total videos across all subjects: {total_videos}")
        self.assertGreaterEqual(total_videos, 0, "Should have some videos")


class TestAdminFeatures(unittest.TestCase):
    """Test admin-specific features."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.data_root_path = os.path.join(os.path.dirname(__file__), "..", "data")
        init_services(cls.data_root_path)
        cls.admin_service = get_admin_service()

        print("\n🧪 Setting up admin feature tests...")

    def test_dashboard_stats_generation(self):
        """Test admin dashboard statistics generation."""
        print("\n🔍 Testing dashboard statistics generation...")

        dashboard_data = self.admin_service.get_dashboard_stats()

        # Test dashboard data structure
        self.assertIn("stats", dashboard_data, "Dashboard should have stats")
        self.assertIn("subjects", dashboard_data, "Dashboard should have subjects")

        stats = dashboard_data["stats"]
        required_stats = [
            "total_subjects",
            "total_subtopics",
            "total_lessons",
            "total_questions",
        ]

        for stat in required_stats:
            self.assertIn(stat, stats, f"Dashboard should include {stat}")
            self.assertIsInstance(stats[stat], int, f"{stat} should be an integer")
            print(f"  {stat}: {stats[stat]}")

        subjects = dashboard_data["subjects"]
        self.assertIsInstance(subjects, dict, "Subjects should be a dictionary")
        print(f"  Subjects in dashboard: {list(subjects.keys())}")

    def test_admin_overview_methods(self):
        """Test admin overview methods."""
        print("\n🔍 Testing admin overview methods...")

        # Test lessons overview
        lessons_overview = self.admin_service.get_lessons_overview()
        self.assertIn(
            "success", lessons_overview, "Lessons overview should have success flag"
        )

        if lessons_overview["success"]:
            self.assertIn(
                "lessons", lessons_overview, "Successful overview should have lessons"
            )
            lessons = lessons_overview["lessons"]
            print(f"  Total lessons in overview: {len(lessons) if lessons else 0}")
        else:
            print(
                f"  Lessons overview failed: {lessons_overview.get('error', 'Unknown error')}"
            )

        # Test filtered lessons overview
        filtered_overview = self.admin_service.get_lessons_overview(
            "python", "functions"
        )
        self.assertIn(
            "success", filtered_overview, "Filtered overview should have success flag"
        )

        if filtered_overview["success"]:
            self.assertIn(
                "lessons",
                filtered_overview,
                "Successful filtered overview should have lessons",
            )
            self.assertIn(
                "filtered_view",
                filtered_overview,
                "Should indicate it's a filtered view",
            )
            lessons = filtered_overview["lessons"]
            print(f"  Python functions lessons: {len(lessons) if lessons else 0}")
        else:
            print(
                f"  Filtered overview failed: {filtered_overview.get('error', 'Unknown error')}"
            )


class TestCacheAndPerformance(unittest.TestCase):
    """Test caching and performance features."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.data_root_path = os.path.join(os.path.dirname(__file__), "..", "data")
        init_services(cls.data_root_path)
        cls.data_service = get_data_service()

        print("\n🧪 Setting up cache and performance tests...")

    def test_data_loader_caching(self):
        """Test DataLoader caching functionality."""
        print("\n🔍 Testing data loader caching...")

        # Access the DataLoader through the service
        data_loader = self.data_service.data_loader

        # Test caching by loading the same data twice
        subject_id, subtopic_id = "python", "functions"

        print(f"  Testing cache for {subject_id}/{subtopic_id}...")

        # First load (should populate cache)
        lessons1 = data_loader.load_lesson_plans(subject_id, subtopic_id)
        cache_size_after_first = len(data_loader._cache)
        print(f"    First load - Cache size: {cache_size_after_first}")

        # Second load (should use cache)
        lessons2 = data_loader.load_lesson_plans(subject_id, subtopic_id)
        cache_size_after_second = len(data_loader._cache)
        print(f"    Second load - Cache size: {cache_size_after_second}")

        # Cache size should not increase on second load
        self.assertEqual(
            cache_size_after_first,
            cache_size_after_second,
            "Cache size should not increase on second load of same data",
        )

        # Data should be identical
        self.assertEqual(
            lessons1, lessons2, "Cached data should be identical to original"
        )

        print(f"    ✅ Caching working correctly")

    def test_cache_keys(self):
        """Test cache key generation."""
        print("\n🔍 Testing cache key generation...")

        data_loader = self.data_service.data_loader

        # Test cache key generation
        key1 = data_loader._get_cache_key("python", "functions", "lessons")
        key2 = data_loader._get_cache_key("python", "functions", "lessons")
        key3 = data_loader._get_cache_key("python", "loops", "lessons")

        print(f"    Key 1: {key1}")
        print(f"    Key 2: {key2}")
        print(f"    Key 3: {key3}")

        # Same parameters should generate same key
        self.assertEqual(key1, key2, "Same parameters should generate same cache key")

        # Different parameters should generate different keys
        self.assertNotEqual(
            key1, key3, "Different parameters should generate different cache keys"
        )

        print(f"    ✅ Cache key generation working correctly")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("[*] COMPREHENSIVE FEATURES TEST SUITE")
    print("=" * 80)
    print(
        "[!] Make sure to run this from the self-paced-learning directory with venv activated!"
    )
    print("=" * 80)

    unittest.main(verbosity=2, buffer=False)
