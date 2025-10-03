"""Test Runner Script

Runs comprehensive tests to identify and diagnose issues
in the refactored Flask application.
"""

import os
import sys
import subprocess


def run_test_file(test_file):
    """Run a specific test file."""
    print(f"\n{'='*80}")
    print(f"🧪 RUNNING: {test_file}")
    print(f"{'='*80}")

    try:
        result = subprocess.run(
            [sys.executable, test_file],
            cwd=os.path.dirname(__file__),
            capture_output=False,  # Show output in real-time
            text=True,
        )

        if result.returncode == 0:
            print(f"\n✅ {test_file} PASSED")
        else:
            print(f"\n❌ {test_file} FAILED (exit code: {result.returncode})")

        return result.returncode == 0

    except Exception as e:
        print(f"\n💥 ERROR running {test_file}: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "🚀" * 30)
    print("  COMPREHENSIVE APPLICATION TESTING")
    print("🚀" * 30)

    test_files = ["test_application.py", "test_flask_routes.py"]

    results = {}

    for test_file in test_files:
        test_path = os.path.join(os.path.dirname(__file__), test_file)
        if os.path.exists(test_path):
            results[test_file] = run_test_file(test_path)
        else:
            print(f"\n⚠️  Test file not found: {test_file}")
            results[test_file] = False

    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)

    passed = 0
    failed = 0

    for test_file, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {test_file}: {status}")

        if success:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")

    if failed > 0:
        print("\n🔧 Issues found! Check the output above for details.")
        return 1
    else:
        print("\n🎉 All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
