#!/usr/bin/env python3
"""
Debug Loops Lessons - Check why loops lessons aren't showing
"""
import sys
import os
import json

# Add the parent directory to the path so we can import the application
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.data_service import DataService


def debug_loops_lessons():
    print("=" * 60)
    print("[*] DEBUGGING LOOPS LESSONS")
    print("=" * 60)

    # Initialize data service
    data_root_path = os.path.join(os.path.dirname(__file__), "data")
    data_service = DataService(data_root_path)
    print("[+] DataService initialized")

    # Check subjects
    print("\n[*] Checking subjects...")
    subjects = data_service.discover_subjects()
    print(f"    [+] Found subjects: {list(subjects.keys())}")

    # Check python subject config
    print("\n[*] Checking python subject config...")
    config = data_service.data_loader.load_subject_config("python")
    if config and "subtopics" in config:
        subtopics = list(config["subtopics"].keys())
        print(f"    [+] Python subtopics: {subtopics}")

        # Check if loops is in there
        if "loops" in subtopics:
            print("    [+] 'loops' subtopic found in config!")
        else:
            print("    [!] 'loops' subtopic NOT found in config!")
    else:
        print("    [!] No python config or subtopics found!")

    # Try to load loops lessons directly
    print("\n[*] Trying to load loops lessons...")
    loops_lessons = data_service.get_lesson_plans("python", "loops")

    if loops_lessons:
        print(f"    [+] Found {len(loops_lessons)} loops lessons:")
        for i, lesson in enumerate(loops_lessons):
            lesson_id = lesson.get("id", f"lesson_{i}")
            lesson_title = lesson.get("title", "No title")
            lesson_order = lesson.get("order", "No order")
            print(
                f"        [{i+1}] ID: {lesson_id}, Title: {lesson_title}, Order: {lesson_order}"
            )
    else:
        print("    [!] No loops lessons found!")

    # Check the raw file
    print("\n[*] Checking raw loops lesson file...")
    loops_file = os.path.join(
        data_service.data_root_path, "subjects", "python", "loops", "lesson_plans.json"
    )

    if os.path.exists(loops_file):
        print(f"    [+] File exists: {loops_file}")
        try:
            with open(loops_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            if "lessons" in raw_data:
                lessons_dict = raw_data["lessons"]
                print(f"    [+] Raw file has {len(lessons_dict)} lesson objects:")
                for lesson_id in list(lessons_dict.keys())[:5]:  # Show first 5
                    lesson_data = lessons_dict[lesson_id]
                    title = lesson_data.get("title", "No title")
                    order = lesson_data.get("order", "No order")
                    print(f"        - {lesson_id}: {title} (order: {order})")

                if len(lessons_dict) > 5:
                    print(f"        ... and {len(lessons_dict) - 5} more")
            else:
                print("    [!] No 'lessons' key in raw file!")
                print(f"    [!] File keys: {list(raw_data.keys())}")

        except Exception as e:
            print(f"    [!] Error reading file: {e}")
    else:
        print(f"    [!] File does not exist: {loops_file}")

    # Check what the Flask app would get
    print("\n[*] Testing Flask app route simulation...")
    try:
        from app_refactored import app

        with app.test_client() as client:
            # Simulate the route that loads lessons
            response = client.get("/api/lessons/python/loops")
            if response.status_code == 200:
                lesson_data = response.get_json()
                if lesson_data:
                    print(f"    [+] API returned {len(lesson_data)} lessons")
                else:
                    print("    [!] API returned empty data")
            else:
                print(f"    [!] API request failed with status {response.status_code}")
    except Exception as e:
        print(f"    [!] Flask app test error: {e}")


if __name__ == "__main__":
    debug_loops_lessons()
