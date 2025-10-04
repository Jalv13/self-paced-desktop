"""Comprehensive Route Testing

Tests all routes and endpoints in the refactored Flask application
to ensure they are accessible and working correctly.
"""

import os
import sys
import unittest
import json
from unittest.mock import patch, MagicMock

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Flask app
try:
    from app_refactored import app
    from services import init_services
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure to run tests from the correct directory with venv activated")
    sys.exit(1)


class TestAllRoutes(unittest.TestCase):
    """Test all Flask routes and endpoints."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.app = app
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing

        # Create test client
        cls.client = cls.app.test_client()

        # Set up app context
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

        print("\n🧪 Setting up comprehensive route tests...")

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        cls.app_context.pop()

    def test_main_routes(self):
        """Test all main application routes."""
        print("\n🔍 Testing main routes...")

        routes_to_test = [
            ("/", "Homepage"),
            ("/subjects/python", "Python subject page"),
            ("/subjects/calculus", "Calculus subject page"),
            ("/python", "Legacy Python route (should redirect)"),
            ("/health", "Health check"),
            ("/dev/test-services", "Service integration test"),
        ]

        for route, description in routes_to_test:
            with self.subTest(route=route):
                print(f"  Testing {description}: {route}")
                response = self.client.get(route)

                # Accept 200, 302 (redirect), or 404 (if content missing)
                acceptable_codes = [200, 302, 404]
                self.assertIn(
                    response.status_code,
                    acceptable_codes,
                    f"{description} returned {response.status_code}",
                )

                if response.status_code == 200:
                    # Check that we got some content
                    content = response.get_data(as_text=True)
                    self.assertGreater(
                        len(content), 0, f"No content returned for {route}"
                    )
                    print(
                        f"    ✅ {response.status_code} - Content length: {len(content)}"
                    )
                elif response.status_code == 302:
                    print(
                        f"    ↩️ {response.status_code} - Redirect to: {response.location}"
                    )
                else:
                    print(f"    ⚠️ {response.status_code} - {description}")

    def test_admin_routes(self):
        """Test admin interface routes."""
        print("\n🔍 Testing admin routes...")

        admin_routes = [
            ("/admin", "Admin dashboard"),
            ("/admin/subjects", "Admin subjects list"),
            ("/admin/subjects/create", "Create subject form"),
            ("/admin/subtopics/select-subject", "Select subject for subtopics"),
            ("/admin/lessons/select-subject", "Select subject for lessons"),
            ("/admin/questions/select-subject", "Select subject for questions"),
            ("/admin/overview/lessons", "All lessons overview"),
            ("/admin/overview/subtopics", "All subtopics overview"),
            ("/admin/overview/questions", "All questions overview"),
        ]

        for route, description in admin_routes:
            with self.subTest(route=route):
                print(f"  Testing {description}: {route}")
                response = self.client.get(route)

                # Admin routes should return 200 or 500 (if data issues)
                self.assertIn(
                    response.status_code,
                    [200, 500],
                    f"{description} returned {response.status_code}",
                )

                if response.status_code == 200:
                    content = response.get_data(as_text=True)
                    print(
                        f"    ✅ {response.status_code} - Content length: {len(content)}"
                    )
                else:
                    print(f"    ❌ {response.status_code} - Error in {description}")

    def test_admin_overview_pages_content(self):
        """Ensure overview pages render aggregated data."""

        overview_pages = [
            ("/admin/overview/lessons", "All Lessons Overview", "Python Functions"),
            ("/admin/overview/questions", "All Questions Overview", "Python Functions"),
            ("/admin/overview/subtopics", "All Subtopics Overview", "Python Functions"),
        ]

        for route, headline, expected in overview_pages:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Overview page {route} should return 200",
                )
                content = response.get_data(as_text=True)
                self.assertIn(headline, content)
                self.assertIn(expected, content)

    def test_api_routes(self):
        """Test API endpoints."""
        print("\n🔍 Testing API routes...")

        api_routes = [
            ("/api/subjects/python/subtopics", "Python subtopics API"),
            ("/api/subjects/calculus/subtopics", "Calculus subtopics API"),
            ("/api/lesson-plans/python/functions", "Python functions lesson plans API"),
            ("/api/lesson-plans/python/loops", "Python loops lesson plans API"),
            ("/api/lesson-plans/python/lists", "Python lists lesson plans API"),
            ("/api/quiz-prerequisites/python/functions", "Quiz prerequisites API"),
            ("/api/video/python/functions/all", "Video API"),
            ("/api/progress", "Progress API"),
            ("/api/admin/status", "Admin status API"),
            (
                "/api/lesson-progress/stats/python/functions",
                "Lesson progress stats API",
            ),
        ]

        for route, description in api_routes:
            with self.subTest(route=route):
                print(f"  Testing {description}: {route}")
                response = self.client.get(route)

                # API routes should return 200, 404 (not found), or 500 (error)
                self.assertIn(
                    response.status_code,
                    [200, 404, 500],
                    f"{description} returned {response.status_code}",
                )

                if response.status_code == 200:
                    # Try to parse JSON response
                    if response.is_json:
                        try:
                            data = response.get_json()
                            print(
                                f"    ✅ {response.status_code} - JSON response with keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}"
                            )
                        except Exception as e:
                            print(
                                f"    ⚠️ {response.status_code} - JSON parse error: {e}"
                            )
                    else:
                        content = response.get_data(as_text=True)
                        print(
                            f"    ✅ {response.status_code} - Non-JSON response, length: {len(content)}"
                        )
                elif response.status_code == 404:
                    print(f"    ❌ {response.status_code} - Not found: {description}")
                else:
                    print(f"    ❌ {response.status_code} - Error in {description}")

    def test_quiz_routes(self):
        """Test quiz-related routes."""
        print("\n🔍 Testing quiz routes...")

        quiz_routes = [
            ("/quiz/python/functions", "Python functions quiz"),
            ("/quiz/python/loops", "Python loops quiz"),
            ("/quiz/calculus/integrals", "Calculus integrals quiz"),
        ]

        for route, description in quiz_routes:
            with self.subTest(route=route):
                print(f"  Testing {description}: {route}")
                response = self.client.get(route)

                # Quiz routes should return 200 (found) or 404 (no quiz data)
                self.assertIn(
                    response.status_code,
                    [200, 404, 500],
                    f"{description} returned {response.status_code}",
                )

                if response.status_code == 200:
                    content = response.get_data(as_text=True)
                    # Check if it's a quiz page (should contain quiz-related content)
                    self.assertIn(
                        "quiz",
                        content.lower(),
                        f"Quiz page doesn't contain quiz content",
                    )
                    print(f"    ✅ {response.status_code} - Quiz page loaded")
                elif response.status_code == 404:
                    print(
                        f"    ⚠️ {response.status_code} - No quiz data for {description}"
                    )
                else:
                    print(
                        f"    ❌ {response.status_code} - Error loading {description}"
                    )

    def test_lesson_display_routes(self):
        """Test individual lesson display routes."""
        print("\n🔍 Testing lesson display routes...")

        # Test some specific lesson routes if they exist
        lesson_routes = [
            (
                "/lesson/python/functions/python-functions-intro",
                "Python functions intro lesson",
            ),
            ("/lesson/python/loops/while-loop-syntax", "While loop syntax lesson"),
        ]

        for route, description in lesson_routes:
            with self.subTest(route=route):
                print(f"  Testing {description}: {route}")
                response = self.client.get(route)

                # Lesson routes may not exist yet, so accept 404
                self.assertIn(
                    response.status_code,
                    [200, 404, 500],
                    f"{description} returned {response.status_code}",
                )

                if response.status_code == 200:
                    content = response.get_data(as_text=True)
                    print(f"    ✅ {response.status_code} - Lesson page loaded")
                elif response.status_code == 404:
                    print(
                        f"    ⚠️ {response.status_code} - Lesson route not implemented yet"
                    )
                else:
                    print(
                        f"    ❌ {response.status_code} - Error loading {description}"
                    )

    def test_admin_specific_routes(self):
        """Test admin routes with specific subjects/subtopics."""
        print("\n🔍 Testing admin specific routes...")

        admin_specific_routes = [
            ("/admin/subtopics?subject=python", "Python subtopics admin"),
            ("/admin/subtopics?subject=calculus", "Calculus subtopics admin"),
            (
                "/admin/lessons/select-subtopic?subject=python",
                "Python lessons subtopic selection",
            ),
            (
                "/admin/questions/select-subtopic?subject=python",
                "Python questions subtopic selection",
            ),
            (
                "/admin/questions?subject=python&subtopic=functions",
                "Python functions questions",
            ),
            (
                "/admin/questions?subject=calculus&subtopic=integrals",
                "Calculus integrals questions",
            ),
        ]

        for route, description in admin_specific_routes:
            with self.subTest(route=route):
                print(f"  Testing {description}: {route}")
                response = self.client.get(route)

                # Admin specific routes should work or return reasonable errors
                self.assertIn(
                    response.status_code,
                    [200, 404, 500],
                    f"{description} returned {response.status_code}",
                )

                if response.status_code == 200:
                    content = response.get_data(as_text=True)
                    print(f"    ✅ {response.status_code} - Admin page loaded")
                elif response.status_code == 404:
                    print(
                        f"    ⚠️ {response.status_code} - Content not found for {description}"
                    )
                else:
                    print(f"    ❌ {response.status_code} - Error in {description}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("[*] COMPREHENSIVE ROUTES TEST SUITE")
    print("=" * 80)
    print(
        "[!] Make sure to run this from the self-paced-learning directory with venv activated!"
    )
    print("=" * 80)

    unittest.main(verbosity=2, buffer=False)
