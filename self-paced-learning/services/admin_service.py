"""Admin Service Module

Handles all administrative operations including subject management,
lesson administration, and system oversight. Extracts admin logic
from the main application routes.
"""

import os
import json
from typing import Dict, List, Optional, Any
from .data_service import DataService
from .progress_service import ProgressService


class AdminService:
    """Service class for handling administrative operations."""

    def __init__(self, data_service: DataService, progress_service: ProgressService):
        """Initialize the admin service with required dependencies."""
        self.data_service = data_service
        self.progress_service = progress_service

    # ============================================================================
    # DASHBOARD AND OVERVIEW
    # ============================================================================

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Generate comprehensive dashboard statistics."""
        try:
            subjects = self.data_service.discover_subjects()
            stats = {
                "total_subjects": len(subjects),
                "total_subtopics": 0,
                "total_lessons": 0,
                "total_questions": 0,
                "subjects_without_content": 0,
            }

            subjects_data = {}

            for subject_id, subject_info in subjects.items():
                subject_config = self.data_service.load_subject_config(subject_id)

                if subject_config and "subtopics" in subject_config:
                    subtopics = subject_config["subtopics"]
                    stats["total_subtopics"] += len(subtopics)

                    subject_lessons = 0
                    subject_questions = 0

                    for subtopic_id in subtopics.keys():
                        # Count lessons
                        lessons = self.data_service.get_lesson_plans(
                            subject_id, subtopic_id
                        )
                        lesson_count = len(lessons) if lessons else 0
                        subject_lessons += lesson_count

                        # Count questions
                        quiz_data = self.data_service.get_quiz_data(
                            subject_id, subtopic_id
                        )
                        question_count = (
                            len(quiz_data.get("questions", [])) if quiz_data else 0
                        )
                        subject_questions += question_count

                    stats["total_lessons"] += subject_lessons
                    stats["total_questions"] += subject_questions

                    if subject_lessons == 0 and subject_questions == 0:
                        stats["subjects_without_content"] += 1

                    subjects_data[subject_id] = {
                        "name": subject_info.get("name", subject_id.title()),
                        "description": subject_info.get("description", ""),
                        "lessons": subject_lessons,
                        "questions": subject_questions,
                        "subtopics": len(subtopics),
                    }
                else:
                    stats["subjects_without_content"] += 1
                    subjects_data[subject_id] = {
                        "name": subject_info.get("name", subject_id.title()),
                        "description": subject_info.get("description", ""),
                        "lessons": 0,
                        "questions": 0,
                        "subtopics": 0,
                    }

            return {"stats": stats, "subjects": subjects_data}

        except Exception as e:
            print(f"Error generating dashboard stats: {e}")
            return {
                "stats": {
                    "total_subjects": 0,
                    "total_subtopics": 0,
                    "total_lessons": 0,
                    "total_questions": 0,
                    "subjects_without_content": 0,
                },
                "subjects": {},
            }

    # ============================================================================
    # SUBJECT MANAGEMENT
    # ============================================================================

    def create_subject(self, subject_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new subject with validation."""
        try:
            subject_id = subject_data.get("id", "").lower().replace(" ", "_")
            subject_name = subject_data.get("name", "")
            description = subject_data.get("description", "")
            icon = subject_data.get("icon", "fas fa-book")
            color = subject_data.get("color", "#007bff")

            # Validation
            if not subject_id or not subject_name:
                return {"success": False, "error": "Subject ID and name are required"}

            # Check if subject already exists
            subjects = self.data_service.discover_subjects()
            if subject_id in subjects:
                return {"success": False, "error": "Subject already exists"}

            # Prepare subject data structure
            complete_subject_data = {
                "info": {
                    "name": subject_name,
                    "description": description,
                    "icon": icon,
                    "color": color,
                    "created_date": "2025-10-02",
                },
                "config": {"subtopics": {}, "updated_date": "2025-10-02"},
            }

            # Create the subject
            success = self.data_service.create_subject(
                subject_id, complete_subject_data
            )

            if success:
                return {
                    "success": True,
                    "message": "Subject created successfully",
                    "subject_id": subject_id,
                }
            else:
                return {"success": False, "error": "Failed to create subject"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_subject(self, subject_id: str) -> Dict[str, Any]:
        """Delete a subject with validation."""
        try:
            # Validate subject exists
            subjects = self.data_service.discover_subjects()
            if subject_id not in subjects:
                return {"success": False, "error": "Subject not found"}

            # Delete the subject
            success = self.data_service.delete_subject(subject_id)

            if success:
                return {"success": True, "message": "Subject deleted successfully"}
            else:
                return {"success": False, "error": "Failed to delete subject"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============================================================================
    # LESSON MANAGEMENT
    # ============================================================================

    def get_lessons_overview(
        self,
        subject_filter: Optional[str] = None,
        subtopic_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get comprehensive lessons overview with optional filtering."""
        try:
            subjects = self.data_service.discover_subjects()

            if subject_filter and subtopic_filter:
                # Filtered view for specific subject/subtopic
                if not self.data_service.validate_subject_subtopic(
                    subject_filter, subtopic_filter
                ):
                    return {
                        "success": False,
                        "error": f"Subject '{subject_filter}' with subtopic '{subtopic_filter}' not found",
                    }

                lessons = self.data_service.get_lesson_plans(
                    subject_filter, subtopic_filter
                )

                # Add metadata to lessons
                if lessons:
                    for lesson in lessons:
                        lesson["subject"] = subject_filter
                        lesson["subtopic"] = subtopic_filter
                        lesson["subject_name"] = subjects[subject_filter].get(
                            "name", subject_filter.title()
                        )

                        # Get subtopic name
                        subject_config = self.data_service.load_subject_config(
                            subject_filter
                        )
                        if subject_config and "subtopics" in subject_config:
                            subtopic_name = subject_config["subtopics"][
                                subtopic_filter
                            ].get("name", subtopic_filter.title())
                            lesson["subtopic_name"] = subtopic_name

                return {
                    "success": True,
                    "lessons": lessons or [],
                    "filtered_view": True,
                    "subject_filter": subject_filter,
                    "subtopic_filter": subtopic_filter,
                }
            else:
                # Unfiltered view: Get all lessons
                all_lessons = self.data_service.get_all_lessons()

                return {
                    "success": True,
                    "lessons": all_lessons,
                    "filtered_view": False,
                    "subjects": subjects,
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_lesson(self, lesson_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new lesson with validation."""
        try:
            subject = lesson_data.get("subject")
            subtopic = lesson_data.get("subtopic")

            # Validation
            if not subject or not subtopic:
                return {"success": False, "error": "Subject and subtopic are required"}

            if not self.data_service.validate_subject_subtopic(subject, subtopic):
                return {
                    "success": False,
                    "error": "Invalid subject/subtopic combination",
                }

            # Generate lesson ID if not provided
            lesson_id = lesson_data.get("id")
            if not lesson_id:
                # Generate ID from title
                title = lesson_data.get("title", "")
                lesson_id = title.lower().replace(" ", "_").replace("-", "_")
                lesson_data["id"] = lesson_id

            # Set default values
            lesson_data.setdefault("type", "initial")
            lesson_data.setdefault("tags", [])
            lesson_data.setdefault("updated_date", "2025-10-02")

            # Save the lesson
            success = self.data_service.save_lesson_to_file(
                subject, subtopic, lesson_id, lesson_data
            )

            if success:
                return {
                    "success": True,
                    "message": "Lesson created successfully",
                    "lesson_id": lesson_id,
                }
            else:
                return {"success": False, "error": "Failed to save lesson"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_lesson(
        self, subject: str, subtopic: str, lesson_id: str, lesson_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing lesson."""
        try:
            # Validation
            if not self.data_service.validate_subject_subtopic(subject, subtopic):
                return {
                    "success": False,
                    "error": "Invalid subject/subtopic combination",
                }

            # Ensure lesson ID is set
            lesson_data["id"] = lesson_id
            lesson_data["updated_date"] = "2025-10-02"

            # Save the updated lesson
            success = self.data_service.save_lesson_to_file(
                subject, subtopic, lesson_id, lesson_data
            )

            if success:
                return {"success": True, "message": "Lesson updated successfully"}
            else:
                return {"success": False, "error": "Failed to update lesson"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_lesson(
        self, subject: str, subtopic: str, lesson_id: str
    ) -> Dict[str, Any]:
        """Delete a lesson with validation."""
        try:
            # Validation
            if not self.data_service.validate_subject_subtopic(subject, subtopic):
                return {
                    "success": False,
                    "error": "Invalid subject/subtopic combination",
                }

            # Delete the lesson
            success = self.data_service.delete_lesson_from_file(
                subject, subtopic, lesson_id
            )

            if success:
                return {"success": True, "message": "Lesson deleted successfully"}
            else:
                return {
                    "success": False,
                    "error": "Lesson not found or failed to delete",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def reorder_lessons(
        self, subject: str, subtopic: str, lesson_order: List[str]
    ) -> Dict[str, Any]:
        """Reorder lessons for a specific subject/subtopic."""
        try:
            # Get current lessons
            lessons = self.data_service.get_lesson_plans(subject, subtopic)

            if not lessons:
                return {
                    "success": False,
                    "error": "No lessons found for this subject/subtopic",
                }

            # Create a mapping of lesson ID to lesson data
            lesson_map = {lesson.get("id"): lesson for lesson in lessons}

            # Reorder lessons according to the provided order
            reordered_lessons = []
            for lesson_id in lesson_order:
                if lesson_id in lesson_map:
                    reordered_lessons.append(lesson_map[lesson_id])

            # Add any lessons not in the order list to the end
            for lesson in lessons:
                lesson_id = lesson.get("id")
                if lesson_id not in lesson_order:
                    reordered_lessons.append(lesson)

            # Save the reordered lessons
            lesson_file_path = os.path.join(
                self.data_service.data_root_path,
                "subjects",
                subject,
                subtopic,
                "lesson_plans.json",
            )

            lesson_plans_data = {
                "lessons": reordered_lessons,
                "updated_date": "2025-10-02",
            }

            os.makedirs(os.path.dirname(lesson_file_path), exist_ok=True)

            with open(lesson_file_path, "w", encoding="utf-8") as f:
                json.dump(lesson_plans_data, f, indent=2, ensure_ascii=False)

            return {"success": True, "message": "Lessons reordered successfully"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============================================================================
    # QUESTIONS MANAGEMENT
    # ============================================================================

    def get_questions_overview(
        self,
        subject_filter: Optional[str] = None,
        subtopic_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get comprehensive questions overview with optional filtering."""
        try:
            subjects = self.data_service.discover_subjects()
            subjects_data = {}

            stats = {
                "total_initial_questions": 0,
                "total_pool_questions": 0,
                "total_subtopics": 0,
                "subtopics_without_questions": 0,
            }

            for subject_id, subject_info in subjects.items():
                # Skip if filtering by subject and this isn't the one
                if subject_filter and subject_id != subject_filter:
                    continue

                subject_config = self.data_service.load_subject_config(subject_id)

                if subject_config and "subtopics" in subject_config:
                    subject_data = {
                        "name": subject_info.get("name", subject_id),
                        "description": subject_info.get("description", ""),
                        "subtopics": {},
                    }

                    for subtopic_id, subtopic_data in subject_config[
                        "subtopics"
                    ].items():
                        # Skip if filtering by subtopic and this isn't the one
                        if subtopic_filter and subtopic_id != subtopic_filter:
                            continue

                        # Load quiz data and question pool to get counts
                        quiz_data = self.data_service.get_quiz_data(
                            subject_id, subtopic_id
                        )
                        pool_data = self.data_service.get_question_pool_questions(
                            subject_id, subtopic_id
                        )

                        quiz_count = (
                            len(quiz_data.get("questions", [])) if quiz_data else 0
                        )
                        pool_count = len(pool_data) if pool_data else 0

                        subtopic_data["quiz_questions_count"] = quiz_count
                        subtopic_data["pool_questions_count"] = pool_count

                        # Update statistics
                        stats["total_initial_questions"] += quiz_count
                        stats["total_pool_questions"] += pool_count
                        stats["total_subtopics"] += 1

                        if quiz_count == 0 and pool_count == 0:
                            stats["subtopics_without_questions"] += 1

                        subject_data["subtopics"][subtopic_id] = subtopic_data

                    subjects_data[subject_id] = subject_data

            return {
                "success": True,
                "subjects": subjects_data,
                "stats": stats,
                "subject_filter": subject_filter,
                "subtopic_filter": subtopic_filter,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_quiz_questions(
        self,
        subject: str,
        subtopic: str,
        questions: List[Dict],
        quiz_type: str = "initial",
    ) -> Dict[str, Any]:
        """Save quiz questions (initial or pool)."""
        try:
            if quiz_type == "initial":
                quiz_data = {
                    "quiz_title": f"{subject.title()} - {subtopic.title()} Quiz",
                    "questions": questions,
                    "updated_date": "2025-10-02",
                }
                success = self.data_service.save_quiz_data(subject, subtopic, quiz_data)

            elif quiz_type == "pool":
                success = self.data_service.save_question_pool(
                    subject, subtopic, questions
                )

            else:
                return {
                    "success": False,
                    "error": "Invalid quiz type. Must be 'initial' or 'pool'",
                }

            if success:
                return {
                    "success": True,
                    "message": f"{quiz_type.title()} questions saved successfully",
                }
            else:
                return {"success": False, "error": "Failed to save questions"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============================================================================
    # OVERRIDE AND TESTING FUNCTIONALITY
    # ============================================================================

    def toggle_admin_override(self) -> Dict[str, Any]:
        """Toggle admin override status."""
        try:
            new_status = self.progress_service.toggle_admin_override()

            return {
                "success": True,
                "admin_override": new_status,
                "message": f"Admin override {'enabled' if new_status else 'disabled'}",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_admin_status(self) -> Dict[str, Any]:
        """Get current admin override status."""
        return {"admin_override": self.progress_service.get_admin_override_status()}

    def admin_mark_complete(self, subject: str, subtopic: str) -> Dict[str, Any]:
        """Mark a topic as complete for admin override."""
        try:
            success = self.progress_service.admin_mark_complete(subject, subtopic)

            if success:
                return {
                    "success": True,
                    "message": f"Topic {subject}/{subtopic} marked as complete",
                }
            else:
                return {"success": False, "error": "Failed to mark topic as complete"}

        except Exception as e:
            return {"success": False, "error": str(e)}
