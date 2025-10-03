"""Progress Service Module

Handles all learning progress tracking, session management, and user state.
Extracts progress logic from the main application routes.
"""

from flask import session, has_request_context
from typing import Dict, List, Optional, Any
from datetime import datetime


class ProgressService:
    """Service class for handling learning progress and session management."""

    def __init__(self):
        """Initialize the progress service."""
        pass

    # ============================================================================
    # SESSION KEY MANAGEMENT
    # ============================================================================

    def get_session_key(self, subject: str, subtopic: str, key_type: str) -> str:
        """Generate a prefixed session key for a specific subject/subtopic."""
        return f"{subject}_{subtopic}_{key_type}"

    def clear_session_data(self, subject: str, subtopic: str) -> None:
        """Clear all session data for a specific subject/subtopic."""
        session_prefix = f"{subject}_{subtopic}"
        keys_to_remove = [
            key for key in session.keys() if key.startswith(session_prefix)
        ]

        for key in keys_to_remove:
            session.pop(key, None)

    def clear_all_session_data(self) -> None:
        """Clear all session data."""
        session.clear()

    # ============================================================================
    # LESSON PROGRESS TRACKING
    # ============================================================================

    def mark_lesson_complete(self, subject: str, subtopic: str, lesson_id: str) -> bool:
        """Mark a specific lesson as completed."""
        if not has_request_context():
            # Return True when not in request context (for testing)
            return True

        try:
            completed_key = self.get_session_key(subject, subtopic, "completed_lessons")
            completed_lessons = session.get(completed_key, [])

            if lesson_id not in completed_lessons:
                completed_lessons.append(lesson_id)
                session[completed_key] = completed_lessons
                session.permanent = True

            return True
        except Exception as e:
            print(f"Error marking lesson complete: {e}")
            return False

    def is_lesson_complete(self, subject: str, subtopic: str, lesson_id: str) -> bool:
        """Check if a specific lesson is completed."""
        if not has_request_context():
            # Return False when not in request context (for testing)
            return False

        try:
            completed_key = self.get_session_key(subject, subtopic, "completed_lessons")
            completed_lessons = session.get(completed_key, [])
            return lesson_id in completed_lessons
        except Exception as e:
            print(f"Error checking lesson completion: {e}")
            return False

    def get_completed_lessons(self, subject: str, subtopic: str) -> List[str]:
        """Get list of completed lesson IDs for a subject/subtopic."""
        completed_key = self.get_session_key(subject, subtopic, "completed_lessons")
        return session.get(completed_key, [])

    def get_lesson_progress_stats(
        self, subject: str, subtopic: str, total_lessons: int
    ) -> Dict[str, Any]:
        """Get lesson progress statistics for a subject/subtopic."""
        completed_lessons = self.get_completed_lessons(subject, subtopic)
        completed_count = len(completed_lessons)

        return {
            "completed_count": completed_count,
            "total_count": total_lessons,
            "completion_percentage": (
                (completed_count / total_lessons * 100) if total_lessons > 0 else 0
            ),
            "completed_lessons": completed_lessons,
        }

    # ============================================================================
    # VIDEO PROGRESS TRACKING
    # ============================================================================

    def mark_video_complete(self, subject: str, subtopic: str, video_id: str) -> bool:
        """Mark a specific video as watched."""
        try:
            watched_key = self.get_session_key(subject, subtopic, "watched_videos")
            watched_videos = session.get(watched_key, [])

            if video_id not in watched_videos:
                watched_videos.append(video_id)
                session[watched_key] = watched_videos
                session.permanent = True

            return True
        except Exception as e:
            print(f"Error marking video complete: {e}")
            return False

    def is_video_complete(self, subject: str, subtopic: str, video_id: str) -> bool:
        """Check if a specific video is watched."""
        watched_key = self.get_session_key(subject, subtopic, "watched_videos")
        watched_videos = session.get(watched_key, [])
        return video_id in watched_videos

    def get_watched_videos(self, subject: str, subtopic: str) -> List[str]:
        """Get list of watched video IDs for a subject/subtopic."""
        watched_key = self.get_session_key(subject, subtopic, "watched_videos")
        return session.get(watched_key, [])

    def get_video_progress_stats(
        self, subject: str, subtopic: str, total_videos: int
    ) -> Dict[str, Any]:
        """Get video progress statistics for a subject/subtopic."""
        watched_videos = self.get_watched_videos(subject, subtopic)
        watched_count = len(watched_videos)

        return {
            "watched_count": watched_count,
            "total_count": total_videos,
            "completion_percentage": (
                (watched_count / total_videos * 100) if total_videos > 0 else 0
            ),
            "watched_videos": watched_videos,
        }

    # ============================================================================
    # QUIZ PROGRESS TRACKING
    # ============================================================================

    def set_quiz_session_data(
        self, subject: str, subtopic: str, quiz_type: str, questions: List[Dict]
    ) -> None:
        """Set quiz session data for analysis."""
        session[self.get_session_key(subject, subtopic, "current_quiz_type")] = (
            quiz_type
        )
        session[
            self.get_session_key(subject, subtopic, "questions_served_for_analysis")
        ] = questions
        session["current_subject"] = subject
        session["current_subtopic"] = subtopic

    def get_quiz_session_data(self, subject: str, subtopic: str) -> Dict[str, Any]:
        """Get current quiz session data."""
        return {
            "quiz_type": session.get(
                self.get_session_key(subject, subtopic, "current_quiz_type")
            ),
            "questions": session.get(
                self.get_session_key(subject, subtopic, "questions_served_for_analysis")
            ),
            "current_subject": session.get("current_subject"),
            "current_subtopic": session.get("current_subtopic"),
        }

    def clear_quiz_session_data(self, subject: str, subtopic: str) -> None:
        """Clear quiz-specific session data."""
        quiz_keys = [
            self.get_session_key(subject, subtopic, "current_quiz_type"),
            self.get_session_key(subject, subtopic, "questions_served_for_analysis"),
        ]

        for key in quiz_keys:
            session.pop(key, None)

    # ============================================================================
    # OVERALL PROGRESS TRACKING
    # ============================================================================

    def check_subtopic_progress(
        self, subject: str, subtopic: str, total_lessons: int, total_videos: int
    ) -> Dict[str, Any]:
        """Check completion status of all lessons and videos for a subject/subtopic."""
        lesson_stats = self.get_lesson_progress_stats(subject, subtopic, total_lessons)
        video_stats = self.get_video_progress_stats(subject, subtopic, total_videos)

        # Calculate overall completion
        total_items = total_lessons + total_videos
        completed_items = lesson_stats["completed_count"] + video_stats["watched_count"]

        overall_percentage = (
            (completed_items / total_items * 100) if total_items > 0 else 0
        )

        return {
            "lessons": lesson_stats,
            "videos": video_stats,
            "overall": {
                "completed_items": completed_items,
                "total_items": total_items,
                "completion_percentage": overall_percentage,
                "is_complete": overall_percentage >= 100,
            },
        }

    def get_all_progress(self) -> Dict[str, Any]:
        """Get all progress data from the current session."""
        progress_data = {}

        # Extract all progress-related session keys
        for key, value in session.items():
            if "_completed_lessons" in key or "_watched_videos" in key:
                # Parse subject and subtopic from key
                parts = key.split("_")
                if len(parts) >= 3:
                    subject = parts[0]
                    subtopic = parts[1]
                    data_type = "_".join(parts[2:])

                    if subject not in progress_data:
                        progress_data[subject] = {}

                    if subtopic not in progress_data[subject]:
                        progress_data[subject][subtopic] = {}

                    progress_data[subject][subtopic][data_type] = value

        return progress_data

    def update_progress(
        self, subject: str, subtopic: str, item_id: str, item_type: str
    ) -> bool:
        """Universal progress update method."""
        try:
            if item_type == "lesson":
                return self.mark_lesson_complete(subject, subtopic, item_id)
            elif item_type == "video":
                return self.mark_video_complete(subject, subtopic, item_id)
            else:
                return False
        except Exception as e:
            print(f"Error updating progress: {e}")
            return False

    # ============================================================================
    # ADMIN OVERRIDE FUNCTIONALITY
    # ============================================================================

    def toggle_admin_override(self) -> bool:
        """Toggle admin override status for debugging/testing."""
        current_status = session.get("admin_override", False)
        new_status = not current_status
        session["admin_override"] = new_status
        session.permanent = True
        return new_status

    def get_admin_override_status(self) -> bool:
        """Get current admin override status."""
        return session.get("admin_override", False)

    def admin_mark_complete(self, subject: str, subtopic: str) -> bool:
        """Mark a topic as complete for admin override functionality."""
        try:
            # This is a simplified implementation - in a real system,
            # you might want to mark all lessons and videos as complete
            override_key = self.get_session_key(subject, subtopic, "admin_complete")
            session[override_key] = True
            session.permanent = True
            return True
        except Exception as e:
            print(f"Error in admin mark complete: {e}")
            return False

    def is_admin_complete(self, subject: str, subtopic: str) -> bool:
        """Check if topic is marked as complete by admin override."""
        override_key = self.get_session_key(subject, subtopic, "admin_complete")
        return session.get(override_key, False)

    # ============================================================================
    # PREREQUISITE CHECKING
    # ============================================================================

    def check_quiz_prerequisites(self, subject: str, subtopic: str) -> Dict[str, Any]:
        """Check prerequisite status for a subject/subtopic.

        Currently returns permissive status (no prerequisites).
        This can be extended to implement actual prerequisite logic.
        """
        return {
            "has_prerequisites": False,
            "prerequisites_met": True,
            "missing_prerequisites": [],
            "can_take_quiz": True,
        }
