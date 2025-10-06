"""Data Service Module

Handles all data loading, saving, and file operations for the learning platform.
Extracts data access logic from the main application routes.
"""

import os
import json
from utils.data_loader import DataLoader
from typing import Dict, List, Optional, Any


def _default_data_root() -> str:
    """Return the default absolute path to the bundled data directory."""

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    return os.path.join(project_root, "data")


class DataService:
    """Service class for handling all data operations."""

    def __init__(self, data_root_path: Optional[str] = None):
        """Initialize the data service with the root data path.

        Args:
            data_root_path: Optional explicit path to the data directory. When
                omitted the service falls back to the repository's bundled
                ``data`` directory.  This mirrors the historic behaviour used
                throughout the tests, allowing ``DataService()`` to work
                without requiring a caller-provided path.
        """

        resolved_path = data_root_path or _default_data_root()
        self.data_root_path = os.path.abspath(resolved_path)
        self.data_loader = DataLoader(self.data_root_path)

    # ============================================================================
    # QUIZ DATA OPERATIONS
    # ============================================================================

    def get_quiz_data(self, subject: str, subtopic: str) -> Optional[List[Dict]]:
        """Load quiz questions for a specific subject/subtopic."""
        return self.data_loader.load_quiz_data(subject, subtopic)

    def get_quiz_title(self, subject: str, subtopic: str) -> str:
        """Get quiz title for a subject/subtopic."""
        return self.data_loader.get_quiz_title(subject, subtopic)

    def save_quiz_data(self, subject: str, subtopic: str, quiz_data: Dict) -> bool:
        """Save quiz data to file."""
        try:
            quiz_file_path = os.path.join(
                self.data_root_path, "subjects", subject, subtopic, "quiz_data.json"
            )

            # Ensure directory exists
            os.makedirs(os.path.dirname(quiz_file_path), exist_ok=True)

            with open(quiz_file_path, "w", encoding="utf-8") as f:
                json.dump(quiz_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Error saving quiz data: {e}")
            return False

    def get_question_pool_questions(
        self, subject: str, subtopic: str
    ) -> Optional[List[Dict]]:
        """Get question pool questions for remedial quizzes."""
        return self.data_loader.get_question_pool_questions(subject, subtopic)

    def save_question_pool(
        self, subject: str, subtopic: str, questions: List[Dict]
    ) -> bool:
        """Save question pool data to file."""
        try:
            pool_file_path = os.path.join(
                self.data_root_path, "subjects", subject, subtopic, "question_pool.json"
            )

            # Ensure directory exists
            os.makedirs(os.path.dirname(pool_file_path), exist_ok=True)

            pool_data = {"questions": questions, "updated_date": "2025-10-02"}

            with open(pool_file_path, "w", encoding="utf-8") as f:
                json.dump(pool_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Error saving question pool: {e}")
            return False

    # ============================================================================
    # LESSON DATA OPERATIONS
    # ============================================================================

    def get_lesson_plans(self, subject: str, subtopic: str) -> Optional[List[Dict]]:
        """Load lesson plans for a specific subject/subtopic."""
        lesson_data = self.data_loader.load_lesson_plans(subject, subtopic)

        if not lesson_data or "lessons" not in lesson_data:
            return []

        lessons = lesson_data["lessons"]

        # Convert lessons object to array if needed
        if isinstance(lessons, dict):
            # Convert from {id: lesson_data} to [lesson_data] format
            lesson_list = []
            for lesson_id, lesson_content in lessons.items():
                lesson_content["id"] = lesson_id  # Add ID to lesson content
                lesson_list.append(lesson_content)

            # Sort by order if available
            lesson_list.sort(key=lambda x: x.get("order", 999))
            return lesson_list
        elif isinstance(lessons, list):
            return lessons
        else:
            return []

    def get_all_lessons(self) -> List[Dict]:
        """Get all lessons across all subjects and subtopics."""
        lessons = []
        subjects = self.data_loader.discover_subjects()

        for subject_id, subject_info in subjects.items():
            subject_config = self.data_loader.load_subject_config(subject_id)

            if subject_config and "subtopics" in subject_config:
                for subtopic_id in subject_config["subtopics"].keys():
                    subject_lessons = self.get_lesson_plans(subject_id, subtopic_id)

                    if subject_lessons:
                        for lesson in subject_lessons:
                            lesson["subject"] = subject_id
                            lesson["subtopic"] = subtopic_id
                            lesson["subject_name"] = subject_info.get(
                                "name", subject_id.title()
                            )

                            # Get subtopic name
                            subtopic_name = subject_config["subtopics"][
                                subtopic_id
                            ].get("name", subtopic_id.title())
                            lesson["subtopic_name"] = subtopic_name

                            lessons.append(lesson)

        return lessons

    def save_lesson_to_file(
        self, subject: str, subtopic: str, lesson_id: str, lesson_data: Dict
    ) -> bool:
        """Save a lesson to the lesson_plans.json file."""
        try:
            lesson_file_path = os.path.join(
                self.data_root_path, "subjects", subject, subtopic, "lesson_plans.json"
            )

            # Load existing lessons or create new structure
            lessons = []
            if os.path.exists(lesson_file_path):
                with open(lesson_file_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                    lessons = existing_data.get("lessons", [])

            # Find and update existing lesson or add new one
            lesson_found = False
            for i, lesson in enumerate(lessons):
                if lesson.get("id") == lesson_id:
                    lessons[i] = lesson_data
                    lesson_found = True
                    break

            if not lesson_found:
                lessons.append(lesson_data)

            # Create the complete lesson plans structure
            lesson_plans_data = {"lessons": lessons, "updated_date": "2025-10-02"}

            # Ensure directory exists
            os.makedirs(os.path.dirname(lesson_file_path), exist_ok=True)

            with open(lesson_file_path, "w", encoding="utf-8") as f:
                json.dump(lesson_plans_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Error saving lesson: {e}")
            return False

    def delete_lesson_from_file(
        self, subject: str, subtopic: str, lesson_id: str
    ) -> bool:
        """Delete a lesson from the lesson_plans.json file."""
        try:
            lesson_file_path = os.path.join(
                self.data_root_path, "subjects", subject, subtopic, "lesson_plans.json"
            )

            if not os.path.exists(lesson_file_path):
                return False

            with open(lesson_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            lessons = data.get("lessons", [])
            original_count = len(lessons)

            # Remove the lesson with matching ID
            lessons = [lesson for lesson in lessons if lesson.get("id") != lesson_id]

            if len(lessons) == original_count:
                return False  # Lesson not found

            # Update the data structure
            data["lessons"] = lessons
            data["updated_date"] = "2025-10-02"

            with open(lesson_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Error deleting lesson: {e}")
            return False

    # ============================================================================
    # VIDEO DATA OPERATIONS
    # ============================================================================

    def get_video_data(self, subject: str, subtopic: str) -> Optional[Dict]:
        """Load and normalise video data for a specific subject/subtopic."""

        raw_data = self.data_loader.load_videos(subject, subtopic) or {}
        videos_payload = raw_data.get("videos", {})

        video_list: List[Dict[str, Any]] = []
        video_map: Dict[str, Dict[str, Any]] = {}

        if isinstance(videos_payload, dict):
            for index, (video_id, video) in enumerate(videos_payload.items()):
                normalised = {"id": video_id, **(video or {})}
                video_list.append(normalised)
                video_map[video_id] = normalised
        elif isinstance(videos_payload, list):
            for index, video in enumerate(videos_payload):
                candidate_id = None
                if isinstance(video, dict):
                    candidate_id = (
                        video.get("id")
                        or video.get("video_id")
                        or video.get("topic_key")
                    )
                video_id = candidate_id or f"video_{index + 1}"
                normalised = {"id": video_id, **(video or {})}
                video_list.append(normalised)
                video_map[video_id] = normalised

        normalised_data = {**raw_data, "videos": video_list}
        if video_map:
            normalised_data["video_map"] = video_map

        return normalised_data

    def get_video_by_topic(
        self, subject: str, subtopic: str, topic_key: str
    ) -> Optional[Dict]:
        """Get specific video by topic key."""
        video_data = self.get_video_data(subject, subtopic) or {}
        video_map = video_data.get("video_map", {})

        if topic_key in video_map:
            return video_map[topic_key]

        for video in video_data.get("videos", []):
            if not isinstance(video, dict):
                continue
            if video.get("topic_key") == topic_key or video.get("id") == topic_key:
                return video

        return None

    # ============================================================================
    # SUBJECT AND SUBTOPIC OPERATIONS
    # ============================================================================

    def discover_subjects(self) -> Dict[str, Dict]:
        """Discover all available subjects."""
        return self.data_loader.discover_subjects()

    def load_subject_config(self, subject: str) -> Optional[Dict]:
        """Load subject configuration."""
        return self.data_loader.load_subject_config(subject)

    def load_subject_info(self, subject: str) -> Optional[Dict]:
        """Load subject information."""
        return self.data_loader.load_subject_info(subject)

    def validate_subject_subtopic(self, subject: str, subtopic: str) -> bool:
        """Validate that a subject/subtopic combination exists."""
        return self.data_loader.validate_subject_subtopic(subject, subtopic)

    def create_subject(self, subject_id: str, subject_data: Dict) -> bool:
        """Create a new subject with its directory structure and files."""
        try:
            subject_dir = os.path.join(self.data_root_path, "subjects", subject_id)

            # Check if subject already exists
            if os.path.exists(subject_dir):
                return False

            # Create subject directory
            os.makedirs(subject_dir, exist_ok=True)

            # Create subject_info.json
            subject_info_path = os.path.join(subject_dir, "subject_info.json")
            with open(subject_info_path, "w", encoding="utf-8") as f:
                json.dump(subject_data["info"], f, indent=2, ensure_ascii=False)

            # Create subject_config.json
            subject_config_path = os.path.join(subject_dir, "subject_config.json")
            with open(subject_config_path, "w", encoding="utf-8") as f:
                json.dump(subject_data["config"], f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Error creating subject: {e}")
            return False

    def delete_subject(self, subject_id: str) -> bool:
        """Delete a subject and all its associated data."""
        try:
            import shutil

            subject_dir = os.path.join(self.data_root_path, "subjects", subject_id)

            if os.path.exists(subject_dir):
                shutil.rmtree(subject_dir)
                return True

            return False
        except Exception as e:
            print(f"Error deleting subject: {e}")
            return False

    # ============================================================================
    # UTILITY METHODS
    # ============================================================================

    def get_subject_allowed_tags(self, subject: str) -> List[str]:
        """Get configured allowed tags for a subject."""
        try:
            tags = self.data_loader.get_subject_keywords(subject)
            return [tag for tag in tags if isinstance(tag, str)]
        except Exception as exc:
            print(f'Error retrieving allowed tags for subject {subject}: {exc}')
            return []

    def get_subject_tags(self, subject: str) -> List[str]:
        """Get all available tags for a subject."""
        tags = set()

        # Get subject config to find all subtopics
        subject_config = self.load_subject_config(subject)

        if subject_config and "subtopics" in subject_config:
            for subtopic_id in subject_config["subtopics"].keys():
                lessons = self.get_lesson_plans(subject, subtopic_id)

                if lessons:
                    for lesson in lessons:
                        lesson_tags = lesson.get("tags", [])
                        if isinstance(lesson_tags, list):
                            tags.update(lesson_tags)

        return sorted(list(tags))

    def find_lessons_by_tags(
        self, subject: str, required_tags: List[str]
    ) -> List[Dict]:
        """Find lessons that contain all required tags."""
        matching_lessons = []
        subject_config = self.load_subject_config(subject)

        if subject_config and "subtopics" in subject_config:
            for subtopic_id in subject_config["subtopics"].keys():
                lessons = self.get_lesson_plans(subject, subtopic_id)

                if lessons:
                    for lesson in lessons:
                        lesson_tags = lesson.get("tags", [])

                        # Check if lesson contains all required tags
                        if all(tag in lesson_tags for tag in required_tags):
                            lesson_copy = lesson.copy()
                            lesson_copy["subject"] = subject
                            lesson_copy["subtopic"] = subtopic_id
                            matching_lessons.append(lesson_copy)

        return matching_lessons

    # ============================================================================
    # CACHE OPERATIONS
    # ============================================================================

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.data_loader.clear_cache()

    def clear_cache_for_subject_subtopic(self, subject: str, subtopic: str) -> None:
        """Clear cache for specific subject/subtopic."""
        self.data_loader.clear_cache_for_subject_subtopic(subject, subtopic)

    def clear_cache_for_subject(self, subject: str) -> None:
        """Clear all cached data for a subject."""
        self.data_loader.clear_cache_for_subject(subject)
