"""Comprehensive Test Runner

Runs all test suites to validate the complete refactored application.
This script runs tests for routes, features, quizzes, and core functionality.
"""

import os
import sys
import subprocess
import time


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"[*] {title}")
    print("=" * 80)


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "-" * 60)
    print(f"[*] {title}")
    print("-" * 60)


def run_test_file(test_file, description):
    """Run a specific test file and return success status."""
    print_section(f"RUNNING: {description}")
    print(f"📁 File: {test_file}")

    try:
        # Run the test file
        result = subprocess.run(
            [sys.executable, test_file],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        # Print output
        if result.stdout:
            print("\n📤 STDOUT:")
            print(result.stdout)

        if result.stderr:
            print("\n📤 STDERR:")
            print(result.stderr)

        # Check result
        if result.returncode == 0:
            print(f"\n✅ {description} PASSED")
            return True
        else:
            print(f"\n❌ {description} FAILED (exit code: {result.returncode})")
            return False

    except subprocess.TimeoutExpired:
        print(f"\n⏰ {description} TIMED OUT (5 minutes)")
        return False
    except Exception as e:
        print(f"\n💥 ERROR running {description}: {e}")
        return False


def check_environment():
    """Check if the environment is set up correctly."""
    print_section("ENVIRONMENT CHECK")

    # Check current directory
    current_dir = os.getcwd()
    expected_dir = "self-paced-learning"

    if expected_dir not in current_dir:
        print(f"⚠️ WARNING: Current directory might not be correct")
        print(f"   Current: {current_dir}")
        print(f"   Expected to contain: {expected_dir}")
        print(f"   You should run this from the self-paced-learning directory")
    else:
        print(f"✅ Directory check passed: {current_dir}")

    # Check if required files exist
    required_files = [
        "../app_refactored.py",
        "../services/__init__.py",
        "../utils/data_loader.py",
        "../data/subjects.json",
    ]

    missing_files = []
    for file_path in required_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if not os.path.exists(full_path):
            missing_files.append(file_path)

    if missing_files:
        print(f"❌ Missing required files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        print(f"   Make sure you're running from the correct directory")
        return False
    else:
        print(f"✅ All required files found")

    # Check Python modules
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import flask
        import services

        print(f"✅ Required Python modules available")
        print(f"   Flask version: {flask.__version__}")
    except ImportError as e:
        print(f"❌ Missing required Python modules: {e}")
        print(f"   Make sure virtual environment is activated")
        print(f"   Run: pip install -r requirements.txt")
        return False

    return True


def main():
    """Run all comprehensive tests."""
    print_header("COMPREHENSIVE APPLICATION TEST SUITE")
    print("[*] Testing the complete refactored Flask application")
    print(
        "[!] Make sure you're in the self-paced-learning directory with venv activated!"
    )

    # Check environment first
    if not check_environment():
        print("\n❌ Environment check failed. Please fix issues before running tests.")
        return 1

    # Define test files to run
    test_files = [
        {
            "file": "test_application.py",
            "description": "Core Application Data and Services Tests",
        },
        {
            "file": "test_features_comprehensive.py",
            "description": "Comprehensive Feature Tests (Data Management, Admin, Cache)",
        },
        {
            "file": "test_routes_comprehensive.py",
            "description": "Comprehensive Route Tests (All Endpoints)",
        },
        {
            "file": "test_quiz_functionality.py",
            "description": "Quiz Functionality Tests (Quizzes, Questions, Results)",
        },
    ]

    # Track results
    results = {}
    start_time = time.time()

    # Run each test file
    for test_info in test_files:
        test_file = test_info["file"]
        description = test_info["description"]

        # Check if test file exists
        test_path = os.path.join(os.path.dirname(__file__), test_file)
        if not os.path.exists(test_path):
            print(f"\n⚠️ Test file not found: {test_file}")
            results[test_file] = False
            continue

        # Run the test
        success = run_test_file(test_file, description)
        results[test_file] = success

    # Calculate total time
    total_time = time.time() - start_time

    # Print final summary
    print_header("TEST SUITE SUMMARY")

    passed = 0
    failed = 0

    for test_file, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {test_file:<40} {status}")

        if success:
            passed += 1
        else:
            failed += 1

    print(f"\n📊 RESULTS:")
    print(f"   Total test files: {len(results)}")
    print(f"   Passed: {passed}")
    print(f"   Failed: {failed}")
    print(f"   Execution time: {total_time:.2f} seconds")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! The refactored application is working correctly.")
        print("\n✅ Summary of what's working:")
        print("   - Core data loading and services")
        print("   - All routes and endpoints accessible")
        print("   - Feature functionality (lessons, quizzes, admin)")
        print("   - Quiz system and question management")
        print("   - Cache and performance features")
        return 0
    else:
        print(f"\n⚠️ {failed} test file(s) failed. Check the output above for details.")
        print("\n🔧 Common issues to check:")
        print("   - Virtual environment activated?")
        print("   - Running from correct directory?")
        print("   - All dependencies installed?")
        print("   - Data files present and valid?")
        return 1


if __name__ == "__main__":
    sys.exit(main())
