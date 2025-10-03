#!/usr/bin/env python3
"""
Quick test to debug the specific issue with loops lessons
"""
import sys
import os

# Add the parent directory to the path so we can import the application
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import init_services, get_data_service


def test_loops_specifically():
    print("=" * 60)
    print("[*] TESTING LOOPS LESSONS SPECIFICALLY")
    print("=" * 60)

    # Initialize services like the Flask app does
    data_root_path = os.path.join(os.path.dirname(__file__), "data")
    print(f"[*] Data root path: {data_root_path}")

    init_services(data_root_path)
    data_service = get_data_service()
    print("[+] Services initialized")

    # Test the exact sequence the app uses
    print("\n[*] Testing subject discovery...")
    subjects = data_service.discover_subjects()
    print(f"    Found subjects: {list(subjects.keys())}")

    print("\n[*] Testing subject config loading...")
    config = data_service.load_subject_config("python")
    if config and "subtopics" in config:
        subtopics = list(config["subtopics"].keys())
        print(f"    Python subtopics: {subtopics}")

        if "loops" in subtopics:
            print("    [+] 'loops' found in config!")

            print("\n[*] Testing lesson plans loading...")
            lesson_plans = data_service.get_lesson_plans("python", "loops")

            if lesson_plans:
                print(f"    [+] get_lesson_plans returned {len(lesson_plans)} lessons")
                for i, lesson in enumerate(lesson_plans):
                    print(
                        f"        {i+1}. {lesson.get('id', 'NO_ID')}: {lesson.get('title', 'NO_TITLE')}"
                    )
            else:
                print("    [!] get_lesson_plans returned None or empty!")

            # Also test what the main routes utility function would return
            print("\n[*] Testing main routes utility function...")
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "blueprints"))

            try:
                from main_routes import get_lesson_plans as main_get_lesson_plans

                main_lessons = main_get_lesson_plans("python", "loops")

                if main_lessons:
                    print(
                        f"    [+] main_routes.get_lesson_plans returned {len(main_lessons)} lessons"
                    )
                else:
                    print(
                        "    [!] main_routes.get_lesson_plans returned None or empty!"
                    )
            except Exception as e:
                print(f"    [!] Error calling main_routes function: {e}")
        else:
            print("    [!] 'loops' NOT found in config!")
    else:
        print("    [!] No python config found!")


if __name__ == "__main__":
    test_loops_specifically()
