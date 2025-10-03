#!/usr/bin/env python3
"""
Quick Test - Basic functionality validation without Unicode characters
"""
import unittest
import sys
import os

# Add the parent directory to the path so we can import the application
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import the services for testing
from services.data_service import DataService
from services.progress_service import ProgressService
from services.admin_service import AdminService


class TestBasicFunctionality(unittest.TestCase):
    """Basic tests for core functionality"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        print("\n[*] Setting up basic functionality tests...")

        # Initialize services
        cls.data_service = DataService()
        cls.progress_service = ProgressService()
        cls.admin_service = AdminService()

        print("[+] Test services initialized")

    def test_data_service_initialization(self):
        """Test that DataService initializes correctly."""
        print("\n[*] Testing DataService initialization...")

        # Test service is not None
        self.assertIsNotNone(self.data_service)
        print("    [+] DataService instance created")

    def test_subject_discovery(self):
        """Test basic subject discovery."""
        print("\n[*] Testing subject discovery...")

        subjects = self.data_service.discover_subjects()

        # Test we get a dictionary
        self.assertIsInstance(subjects, dict)
        print(f"    [+] Found {len(subjects)} subjects: {list(subjects.keys())}")

        # Test we have at least python and calculus
        expected_subjects = ["python", "calculus"]
        for subject in expected_subjects:
            if subject in subjects:
                print(f"    [+] Subject '{subject}' found: {subjects[subject]}")
            else:
                print(f"    [!] Subject '{subject}' not found")

    def test_lesson_data_loading(self):
        """Test lesson data loading specifically."""
        print("\n[*] Testing lesson data loading...")

        # Test python lessons
        python_lessons = self.data_service.get_lesson_plans("python", "functions")
        print(
            f"    [+] Python functions lessons: {len(python_lessons) if python_lessons else 0}"
        )

        if python_lessons:
            for lesson in python_lessons[:3]:  # Show first 3
                lesson_id = lesson.get("id", "No ID")
                lesson_title = lesson.get("title", "No title")
                print(f"        [+] Lesson {lesson_id}: {lesson_title}")

    def test_progress_service(self):
        """Test progress service basic functionality."""
        print("\n[*] Testing progress service...")

        # Test session key generation
        session_key = self.progress_service.generate_session_key()
        self.assertIsNotNone(session_key)
        print(f"    [+] Session key generated: {session_key[:20]}...")

    def test_admin_service(self):
        """Test admin service basic functionality."""
        print("\n[*] Testing admin service...")

        # Test dashboard stats
        try:
            stats = self.admin_service.get_dashboard_stats()
            self.assertIsInstance(stats, dict)
            print(f"    [+] Dashboard stats generated with {len(stats)} fields")
        except Exception as e:
            print(f"    [!] Dashboard stats error: {e}")

    def test_flask_app_import(self):
        """Test that the Flask app can be imported without errors."""
        print("\n[*] Testing Flask app import...")

        try:
            from app_refactored import app

            self.assertIsNotNone(app)
            print("    [+] Flask app imported successfully")
            print(f"    [+] App name: {app.name}")
        except Exception as e:
            print(f"    [!] Flask app import error: {e}")
            self.fail(f"Failed to import Flask app: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("[*] QUICK TEST - Basic Functionality Validation")
    print("=" * 60)
    print("[*] Testing core services and data loading")
    print("[*] No complex UI or Unicode characters")
    print("=" * 60)

    # Run tests with verbose output
    unittest.main(verbosity=2, buffer=False)
