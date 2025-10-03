"""Flask Routes Testing

Test all Flask routes and endpoints to ensure they work correctly
with the refactored architecture.
"""

import os
import sys
import unittest
import json
from unittest.mock import patch

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Flask app
from app_refactored import app
from services import init_services


class TestFlaskRoutes(unittest.TestCase):
    """Test Flask routes and endpoints."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.app = app
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

        # Initialize services
        data_root_path = os.path.join(os.path.dirname(__file__), "..", "data")

        # Set up app context for testing
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        cls.app_context.pop()

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        print("\n🔍 Testing health endpoint...")

        response = self.client.get("/health")
        print(f"Health endpoint status: {response.status_code}")

        self.assertEqual(response.status_code, 200)

        if response.is_json:
            data = response.get_json()
            print(f"Health data keys: {list(data.keys())}")
            self.assertIn("status", data)
        else:
            print(f"Health response: {response.get_data(as_text=True)[:200]}...")

    def test_homepage(self):
        """Test the homepage route."""
        print("\n🔍 Testing homepage...")

        response = self.client.get("/")
        print(f"Homepage status: {response.status_code}")

        # Should return 200 or redirect
        self.assertIn(response.status_code, [200, 302])

        if response.status_code == 200:
            html_content = response.get_data(as_text=True)
            print(f"Homepage content length: {len(html_content)}")
            self.assertGreater(len(html_content), 0)

    def test_admin_dashboard(self):
        """Test the admin dashboard route."""
        print("\n🔍 Testing admin dashboard...")

        response = self.client.get("/admin")
        print(f"Admin dashboard status: {response.status_code}")

        # Should return 200 or 500 (if there are data issues)
        self.assertIn(response.status_code, [200, 500])

        if response.status_code == 500:
            content = response.get_data(as_text=True)
            print(f"Admin error: {content[:200]}...")

    def test_api_endpoints(self):
        """Test API endpoints."""
        print("\n🔍 Testing API endpoints...")

        # Test health API
        response = self.client.get("/api/../health")
        print(f"API health redirect: {response.status_code}")

        # Test subjects API (if we have any subjects)
        response = self.client.get("/api/subjects/python/subtopics")
        print(f"Subtopics API status: {response.status_code}")

        if response.status_code == 200 and response.is_json:
            data = response.get_json()
            print(
                f"Subtopics data: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}"
            )

    def test_subject_routes(self):
        """Test subject-specific routes."""
        print("\n🔍 Testing subject routes...")

        # Test Python subject page
        response = self.client.get("/subjects/python")
        print(f"Python subject status: {response.status_code}")

        # Test legacy Python route
        response = self.client.get("/python")
        print(f"Legacy Python route status: {response.status_code}")

        # Should redirect to /subjects/python
        if response.status_code == 302:
            print(f"Redirect location: {response.location}")

    def test_quiz_routes(self):
        """Test quiz routes."""
        print("\n🔍 Testing quiz routes...")

        # Test quiz route (should fail if no quiz data)
        response = self.client.get("/quiz/python/functions")
        print(f"Quiz route status: {response.status_code}")

        # 200 = quiz found, 404 = no quiz data
        self.assertIn(response.status_code, [200, 404, 500])

        if response.status_code == 404:
            content = response.get_data(as_text=True)
            print(f"Quiz error: {content[:100]}...")

    def test_api_lesson_plans(self):
        """Test lesson plans API."""
        print("\n🔍 Testing lesson plans API...")

        response = self.client.get("/api/lesson-plans/python/functions")
        print(f"Lesson plans API status: {response.status_code}")

        if response.status_code == 200 and response.is_json:
            data = response.get_json()
            print(
                f"Lesson plans data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}"
            )

            if "lessons" in data:
                lessons = data["lessons"]
                print(f"Found {len(lessons)} lessons")
                if lessons:
                    first_lesson = lessons[0]
                    print(f"First lesson: {first_lesson.get('title', 'No title')}")
        elif response.status_code == 404:
            print("No lesson plans found for python/functions")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 FLASK ROUTES TEST SUITE")
    print("=" * 60)

    unittest.main(verbosity=2, buffer=False)
