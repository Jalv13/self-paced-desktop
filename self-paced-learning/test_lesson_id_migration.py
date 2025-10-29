"""Test lesson ID migration functionality."""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.progress_service import ProgressService
from services.data_service import DataService
from services.admin_service import AdminService


def test_lesson_id_migration():
    """Test that lesson ID migration works correctly."""

    print("=" * 60)
    print("Testing Lesson ID Migration")
    print("=" * 60)

    # Initialize services
    progress_service = ProgressService()
    data_service = DataService()
    admin_service = AdminService(data_service, progress_service)

    subject = "python"
    subtopic = "loops"
    old_id = "for-loops"
    new_id = "introduction-to-for-loops"

    # Simulate a completed lesson with old ID
    print(f"\n1. Marking lesson '{old_id}' as complete...")
    progress_service.mark_lesson_complete(subject, subtopic, old_id)

    # Verify it's marked as complete
    is_complete_old = progress_service.is_lesson_complete(subject, subtopic, old_id)
    print(f"   ✓ Lesson '{old_id}' completed: {is_complete_old}")

    completed_lessons = progress_service.get_completed_lessons(subject, subtopic)
    print(f"   Completed lessons: {completed_lessons}")

    # Migrate the lesson ID
    print(f"\n2. Migrating lesson ID from '{old_id}' to '{new_id}'...")
    result = progress_service.migrate_lesson_id(subject, subtopic, old_id, new_id)
    print(f"   Migration result: {result}")

    # Verify old ID is no longer complete
    is_complete_old_after = progress_service.is_lesson_complete(
        subject, subtopic, old_id
    )
    print(f"\n3. Checking old ID '{old_id}' completion: {is_complete_old_after}")

    # Verify new ID is marked as complete
    is_complete_new = progress_service.is_lesson_complete(subject, subtopic, new_id)
    print(f"   Checking new ID '{new_id}' completion: {is_complete_new}")

    completed_lessons_after = progress_service.get_completed_lessons(subject, subtopic)
    print(f"   Completed lessons after migration: {completed_lessons_after}")

    # Test results
    print("\n" + "=" * 60)
    print("TEST RESULTS:")
    print("=" * 60)

    if result.get("success"):
        print("✅ Migration executed successfully")
    else:
        print(f"❌ Migration failed: {result.get('error')}")
        return False

    if not is_complete_old_after:
        print(f"✅ Old ID '{old_id}' is no longer marked as complete")
    else:
        print(f"❌ Old ID '{old_id}' is still marked as complete")
        return False

    if is_complete_new:
        print(f"✅ New ID '{new_id}' is marked as complete")
    else:
        print(f"❌ New ID '{new_id}' is NOT marked as complete")
        return False

    if new_id in completed_lessons_after and old_id not in completed_lessons_after:
        print(f"✅ Completed lessons list updated correctly")
    else:
        print(f"❌ Completed lessons list not updated correctly")
        return False

    print("\n🎉 All tests passed!")
    return True


if __name__ == "__main__":
    try:
        success = test_lesson_id_migration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
