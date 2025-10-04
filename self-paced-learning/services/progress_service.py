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
        self._test_completed_lessons = {}
        self._test_watched_videos = {}

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

        completed_key = self.get_session_key(subject, subtopic, "completed_lessons")
        self._test_completed_lessons.pop(completed_key, None)
        watched_key = self.get_session_key(subject, subtopic, "watched_videos")
        self._test_watched_videos.pop(watched_key, None)

    def clear_all_session_data(self) -> None:
        """Clear all session data."""
        session.clear()
        self._test_completed_lessons.clear()
        self._test_watched_videos.clear()

    # ============================================================================
    # LESSON PROGRESS TRACKING
    # ============================================================================

    def mark_lesson_complete(self, subject: str, subtopic: str, lesson_id: str) -> bool:
        """Mark a specific lesson as completed."""
        if not has_request_context():
            key = self.get_session_key(subject, subtopic, "completed_lessons")
            completed = self._test_completed_lessons.setdefault(key, set())
            completed.add(lesson_id)
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
            key = self.get_session_key(subject, subtopic, "completed_lessons")
            completed = self._test_completed_lessons.get(key, set())
            return lesson_id in completed

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
        if not has_request_context():
            return list(self._test_completed_lessons.get(completed_key, set()))
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
        if not has_request_context():
            key = self.get_session_key(subject, subtopic, "watched_videos")
            watched = self._test_watched_videos.setdefault(key, set())
            watched.add(video_id)
            return True

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
        if not has_request_context():
            watched = self._test_watched_videos.get(watched_key, set())
            return video_id in watched
        watched_videos = session.get(watched_key, [])
        return video_id in watched_videos

    def get_watched_videos(self, subject: str, subtopic: str) -> List[str]:
        """Get list of watched video IDs for a subject/subtopic."""
        watched_key = self.get_session_key(subject, subtopic, "watched_videos")
        if not has_request_context():
            return list(self._test_watched_videos.get(watched_key, set()))
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


    def prepare_analysis_for_session(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Return a sanitized copy of analysis data suitable for cookie storage."""
        if not isinstance(analysis, dict):
            return {}

        keys_to_keep = [
            "score",
            "weak_topics",
            "weak_tags",
            "weak_areas",
            "feedback",
            "ai_analysis",
            "recommendations",
            "allowed_tags",
            "used_ai",
            "analysis_stage",
            "basic_feedback",
            "rule_based_insights",
        ]

        sanitized = {key: analysis.get(key) for key in keys_to_keep if key in analysis}

        submission = analysis.get("submission_details")
        if submission:
            # Provide a short summary for debugging while keeping cookie sizes small
            if isinstance(submission, list):
                preview = "\n".join(str(part) for part in submission)[:1000]
            else:
                preview = str(submission)[:1000]
            sanitized["submission_preview"] = preview

        raw_response = analysis.get("raw_ai_response")
        if raw_response:
            sanitized["raw_ai_response_preview"] = str(raw_response)[:1000]

        return sanitized

    def store_quiz_analysis(self, subject: str, subtopic: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Persist quiz analysis results for later use and return sanitized copy."""
        sanitized = self.prepare_analysis_for_session(analysis)
        key = self.get_session_key(subject, subtopic, "analysis_results")
        session[key] = sanitized
        session.permanent = True
        return sanitized

    def get_quiz_analysis(self, subject: str, subtopic: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored quiz analysis if available."""
        key = self.get_session_key(subject, subtopic, "analysis_results")
        return session.get(key)

    def set_weak_topics(self, subject: str, subtopic: str, topics: List[str]) -> None:
        """Store normalized weak topics for remedial guidance."""
        normalized: List[str] = []
        seen = set()
        for topic in topics or []:
            if not isinstance(topic, str):
                continue
            cleaned = topic.strip()
            if not cleaned:
                continue
            key_lower = cleaned.lower()
            if key_lower in seen:
                continue
            seen.add(key_lower)
            normalized.append(cleaned)
        weak_key = self.get_session_key(subject, subtopic, "weak_topics")
        session[weak_key] = normalized
        session.permanent = True

    def get_weak_topics(self, subject: str, subtopic: str) -> List[str]:
        """Return stored weak topics, if any."""
        weak_key = self.get_session_key(subject, subtopic, "weak_topics")
        return session.get(weak_key, [])

    def set_remedial_quiz_data(
        self, subject: str, subtopic: str, questions: List[Dict[str, Any]], topics: Optional[List[str]] = None
    ) -> None:
        """Persist remedial quiz questions and related topics."""
        questions_key = self.get_session_key(subject, subtopic, "remedial_questions")
        session[questions_key] = questions
        if topics is not None:
            topics_key = self.get_session_key(subject, subtopic, "remedial_topics")
            session[topics_key] = topics
        session.permanent = True

    def get_remedial_quiz_questions(self, subject: str, subtopic: str) -> List[Dict[str, Any]]:
        """Get stored remedial quiz questions."""
        questions_key = self.get_session_key(subject, subtopic, "remedial_questions")
        return session.get(questions_key, [])

    def get_remedial_topics(self, subject: str, subtopic: str) -> List[str]:
        """Get topics associated with the remedial quiz."""
        topics_key = self.get_session_key(subject, subtopic, "remedial_topics")
        return session.get(topics_key, [])

    def clear_remedial_quiz_data(self, subject: str, subtopic: str) -> None:
        """Remove remedial quiz data from the session."""
        for suffix in ("remedial_questions", "remedial_topics"):
            session.pop(self.get_session_key(subject, subtopic, suffix), None)

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
        """Evaluate whether the learner can take the quiz for a subject/subtopic."""

        from services import get_data_service  # Lazy import to avoid circular deps

        data_service = get_data_service()
        loader = data_service.data_loader

        lesson_data = loader.load_lesson_plans(subject, subtopic) or {}
        raw_lessons = lesson_data.get("lessons", {})

        lesson_items = []
        if isinstance(raw_lessons, dict):
            lesson_items = list(raw_lessons.items())
        elif isinstance(raw_lessons, list):
            for index, lesson in enumerate(raw_lessons):
                lesson_id = lesson.get("id") or f"lesson_{index + 1}"
                lesson_items.append((lesson_id, lesson))

        lesson_titles = {
            lesson_id: lesson.get("title", lesson_id)
            for lesson_id, lesson in lesson_items
        }
        lesson_ids = list(lesson_titles.keys())

        completed_lessons = set(self.get_completed_lessons(subject, subtopic))
        missing_lessons = [
            lesson_titles[lesson_id]
            for lesson_id in lesson_ids
            if lesson_id not in completed_lessons
        ]

        videos_data = loader.load_videos(subject, subtopic) or {}
        raw_videos = videos_data.get("videos", {})

        video_titles = {}
        video_ids: List[str] = []
        if isinstance(raw_videos, dict):
            for video_id, video in raw_videos.items():
                video_ids.append(video_id)
                video_titles[video_id] = video.get("title", video_id)
        elif isinstance(raw_videos, list):
            for index, video in enumerate(raw_videos):
                video_id = video.get("id") or f"video_{index + 1}"
                video_ids.append(video_id)
                video_titles[video_id] = video.get("title", video_id)

        watched_videos = set(self.get_watched_videos(subject, subtopic))
        missing_videos = [
            video_titles.get(video_id, video_id)
            for video_id in video_ids
            if video_id not in watched_videos
        ]

        lessons_complete = len(missing_lessons) == 0 if lesson_ids else True
        videos_complete = len(missing_videos) == 0 if video_ids else True

        missing_items: List[str] = []
        missing_items.extend([f"Complete lesson: {title}" for title in missing_lessons])
        missing_items.extend([f"Watch video: {title}" for title in missing_videos])

        admin_override = self.get_admin_override_status()
        all_met = admin_override or (lessons_complete and videos_complete)

        return {
            "subject": subject,
            "subtopic": subtopic,
            "has_prerequisites": bool(lesson_ids or video_ids),
            "lessons_complete": lessons_complete,
            "lesson_total": len(lesson_ids),
            "lessons_completed": len(lesson_ids) - len(missing_lessons),
            "videos_complete": videos_complete,
            "videos_total": len(video_ids),
            "videos_watched": len(video_ids) - len(missing_videos),
            "missing_items": missing_items,
            "missing_lessons": missing_lessons,
            "missing_videos": missing_videos,
            "admin_override": admin_override,
            "all_met": all_met,
            "can_take_quiz": all_met,
            "prerequisites_met": all_met,
        }
