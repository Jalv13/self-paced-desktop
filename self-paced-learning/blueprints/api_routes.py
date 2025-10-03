"""API Routes Blueprint

Handles all API endpoints including video management, progress tracking,
and learning management APIs.
"""

from flask import Blueprint, jsonify, request, session
from services import get_data_service, get_progress_service, get_ai_service
from typing import Dict, List, Optional

# Create the Blueprint
api_bp = Blueprint("api", __name__, url_prefix="/api")


# ============================================================================
# VIDEO API ENDPOINTS
# ============================================================================


@api_bp.route("/video/<topic_key>")
def get_video_api_legacy(topic_key):
    """Legacy video API route for backward compatibility."""
    # This is a legacy route - redirect to new format if possible
    return (
        jsonify(
            {
                "error": "Legacy video API. Please use /api/video/<subject>/<subtopic>/<topic_key>"
            }
        ),
        400,
    )


@api_bp.route("/video/<subject>/<subtopic>/<topic_key>")
def get_video_api(subject, subtopic, topic_key):
    """Get video data for a specific subject/subtopic/topic."""
    try:
        data_service = get_data_service()

        # Validate subject/subtopic exists
        if not data_service.validate_subject_subtopic(subject, subtopic):
            return jsonify({"error": "Subject/subtopic not found"}), 404

        # Get specific video by topic key
        video = data_service.get_video_by_topic(subject, subtopic, topic_key)

        if video:
            return jsonify(video)
        else:
            return jsonify({"error": "Video not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/video/<subject>/<subtopic>/all")
def get_all_videos_api(subject, subtopic):
    """Get all video data for a subject/subtopic."""
    try:
        data_service = get_data_service()

        # Validate subject/subtopic exists
        if not data_service.validate_subject_subtopic(subject, subtopic):
            return jsonify({"error": "Subject/subtopic not found"}), 404

        # Get all videos
        video_data = data_service.get_video_data(subject, subtopic)

        if video_data:
            return jsonify(video_data)
        else:
            return jsonify({"videos": [], "message": "No videos found"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# PROGRESS TRACKING API ENDPOINTS
# ============================================================================


@api_bp.route("/progress/update", methods=["POST"])
def update_progress_api():
    """Universal progress update endpoint."""
    try:
        progress_service = get_progress_service()

        data = request.get_json()
        subject = data.get("subject")
        subtopic = data.get("subtopic")
        item_id = data.get("item_id")
        item_type = data.get("item_type")  # 'lesson' or 'video'

        if not all([subject, subtopic, item_id, item_type]):
            return jsonify({"error": "Missing required fields"}), 400

        success = progress_service.update_progress(
            subject, subtopic, item_id, item_type
        )

        if success:
            return jsonify({"success": True, "message": "Progress updated"})
        else:
            return jsonify({"error": "Failed to update progress"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/lesson-progress/mark-complete", methods=["POST"])
def mark_lesson_complete():
    """Mark a specific lesson as completed."""
    try:
        progress_service = get_progress_service()

        data = request.get_json()
        subject = data.get("subject")
        subtopic = data.get("subtopic")
        lesson_id = data.get("lesson_id")

        if not all([subject, subtopic, lesson_id]):
            return jsonify({"error": "Missing required fields"}), 400

        success = progress_service.mark_lesson_complete(subject, subtopic, lesson_id)

        if success:
            return jsonify({"success": True, "message": "Lesson marked as complete"})
        else:
            return jsonify({"error": "Failed to mark lesson complete"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/video-progress/mark-complete", methods=["POST"])
def mark_video_complete():
    """Mark a specific video as watched."""
    try:
        progress_service = get_progress_service()

        data = request.get_json()
        subject = data.get("subject")
        subtopic = data.get("subtopic")
        video_id = data.get("video_id")

        if not all([subject, subtopic, video_id]):
            return jsonify({"error": "Missing required fields"}), 400

        success = progress_service.mark_video_complete(subject, subtopic, video_id)

        if success:
            return jsonify({"success": True, "message": "Video marked as watched"})
        else:
            return jsonify({"error": "Failed to mark video complete"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/progress/check/<subject>/<subtopic>")
def check_subtopic_progress(subject, subtopic):
    """Check completion status of all lessons and videos for a subject/subtopic."""
    try:
        data_service = get_data_service()
        progress_service = get_progress_service()

        # Validate subject/subtopic exists
        if not data_service.validate_subject_subtopic(subject, subtopic):
            return jsonify({"error": "Subject/subtopic not found"}), 404

        # Get content counts
        lessons = data_service.get_lesson_plans(subject, subtopic)
        videos_data = data_service.get_video_data(subject, subtopic)

        lesson_count = len(lessons) if lessons else 0
        video_count = len(videos_data.get("videos", [])) if videos_data else 0

        # Get progress statistics
        progress_stats = progress_service.check_subtopic_progress(
            subject, subtopic, lesson_count, video_count
        )

        return jsonify(progress_stats)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/progress")
def get_all_progress_api():
    """Get all progress data from the current session."""
    try:
        progress_service = get_progress_service()
        progress_data = progress_service.get_all_progress()

        return jsonify(progress_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# LESSON AND LEARNING MANAGEMENT API ENDPOINTS
# ============================================================================


@api_bp.route("/lesson-plans/<subject>/<subtopic>")
def api_lesson_plans(subject, subtopic):
    """Return lesson plans for a subject/subtopic in a stable shape, with lessons ordered appropriately."""
    try:
        data_service = get_data_service()
        progress_service = get_progress_service()

        # Validate subject/subtopic exists
        if not data_service.validate_subject_subtopic(subject, subtopic):
            return jsonify({"error": "Subject/subtopic not found"}), 404

        # Get lesson plans
        lesson_data = data_service.data_loader.load_lesson_plans(subject, subtopic)

        if not lesson_data or "lessons" not in lesson_data:
            return jsonify({"lessons": {}, "message": "No lessons found"})

        lessons = lesson_data["lessons"]

        # Add progress information to each lesson
        for lesson_id, lesson in lessons.items():
            lesson["completed"] = progress_service.is_lesson_complete(
                subject, subtopic, lesson_id
            )

        return jsonify({"lessons": lessons, "subject": subject, "subtopic": subtopic})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/lesson-progress/stats/<subject>/<subtopic>")
def api_lesson_progress_stats(subject, subtopic):
    """Return lightweight lesson progress stats for a subject/subtopic."""
    try:
        data_service = get_data_service()
        progress_service = get_progress_service()

        # Validate subject/subtopic exists
        if not data_service.validate_subject_subtopic(subject, subtopic):
            return jsonify({"error": "Subject/subtopic not found"}), 404

        # Get lesson count
        lessons = data_service.get_lesson_plans(subject, subtopic)
        total_lessons = len(lessons) if lessons else 0

        # Get progress stats
        stats = progress_service.get_lesson_progress_stats(
            subject, subtopic, total_lessons
        )

        return jsonify(stats)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/lessons/find-by-tags", methods=["POST"])
def api_find_lessons_by_tags():
    """Find lessons that contain all required tags."""
    try:
        data_service = get_data_service()

        data = request.get_json()
        subject = data.get("subject")
        tags = data.get("tags", [])

        if not subject or not tags:
            return jsonify({"error": "Subject and tags are required"}), 400

        # Find lessons by tags
        matching_lessons = data_service.find_lessons_by_tags(subject, tags)

        return jsonify(
            {
                "lessons": matching_lessons,
                "subject": subject,
                "tags": tags,
                "count": len(matching_lessons),
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# SUBJECT AND SUBTOPIC API ENDPOINTS
# ============================================================================


@api_bp.route("/subjects/<subject>/tags")
def api_get_subject_tags(subject):
    """API endpoint to get available tags for a subject."""
    try:
        data_service = get_data_service()

        # Validate subject exists
        subjects = data_service.discover_subjects()
        if subject not in subjects:
            return jsonify({"error": "Subject not found"}), 404

        # Get tags for the subject
        tags = data_service.get_subject_tags(subject)

        return jsonify({"subject": subject, "tags": tags})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/subjects/<subject>/subtopics")
def api_get_subtopics(subject):
    """API endpoint to get subtopics for a subject."""
    try:
        data_service = get_data_service()

        # Validate subject exists
        if not data_service.load_subject_config(subject):
            return jsonify({"error": "Subject not found"}), 404

        # Get subject config
        subject_config = data_service.load_subject_config(subject)
        subtopics = subject_config.get("subtopics", {}) if subject_config else {}

        return jsonify({"subject": subject, "subtopics": subtopics})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# QUIZ AND ASSESSMENT API ENDPOINTS
# ============================================================================


@api_bp.route("/quiz-prerequisites/<subject>/<subtopic>")
def api_quiz_prerequisites(subject, subtopic):
    """Return prerequisite status for a subject/subtopic. Currently permissive (no prerequisites)."""
    try:
        data_service = get_data_service()
        progress_service = get_progress_service()

        # Validate subject/subtopic exists
        if not data_service.validate_subject_subtopic(subject, subtopic):
            return jsonify({"error": "Subject/subtopic not found"}), 404

        # Check prerequisites
        prerequisites = progress_service.check_quiz_prerequisites(subject, subtopic)

        return jsonify(prerequisites)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/recommend_videos", methods=["GET"])
def recommend_videos_api():
    """API endpoint for video recommendations based on quiz performance."""
    try:
        data_service = get_data_service()
        ai_service = get_ai_service()

        subject = request.args.get("subject")
        subtopic = request.args.get("subtopic")
        weak_areas = request.args.getlist("weak_areas")

        if not subject or not subtopic:
            return jsonify({"error": "Subject and subtopic are required"}), 400

        # Validate subject/subtopic exists
        if not data_service.validate_subject_subtopic(subject, subtopic):
            return jsonify({"error": "Subject/subtopic not found"}), 404

        # Get video data
        video_data = data_service.get_video_data(subject, subtopic)
        available_videos = video_data.get("videos", []) if video_data else []

        # Get recommendations
        recommendations = ai_service.recommend_videos(
            subject, subtopic, weak_areas, available_videos
        )

        return jsonify(
            {
                "subject": subject,
                "subtopic": subtopic,
                "weak_areas": weak_areas,
                "recommendations": recommendations,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ADMIN API ENDPOINTS
# ============================================================================


@api_bp.route("/admin/status")
def api_admin_status():
    """Return admin override status expected by frontend."""
    try:
        progress_service = get_progress_service()

        return jsonify({"admin_override": progress_service.get_admin_override_status()})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/admin/mark_complete", methods=["POST"])
def api_admin_mark_complete():
    """Mark a topic as complete for admin override functionality."""
    try:
        progress_service = get_progress_service()

        data = request.get_json()
        subject = data.get("subject")
        subtopic = data.get("subtopic")

        if not subject or not subtopic:
            return jsonify({"error": "Subject and subtopic are required"}), 400

        success = progress_service.admin_mark_complete(subject, subtopic)

        if success:
            return jsonify({"success": True, "message": "Topic marked as complete"})
        else:
            return jsonify({"error": "Failed to mark topic as complete"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500
