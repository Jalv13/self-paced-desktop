"""Main Routes Blueprint

Handles core application routes including subject selection, quiz pages,
and primary user-facing functionality.
"""

from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    request,
    jsonify,
)
from services import get_data_service, get_progress_service, get_ai_service
from typing import Dict, List, Optional, Any

# Create the Blueprint
main_bp = Blueprint("main", __name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_quiz_data(subject: str, subtopic: str) -> Optional[List[Dict]]:
    """Load quiz questions for a specific subject/subtopic."""
    data_service = get_data_service()
    return data_service.data_loader.get_quiz_questions(subject, subtopic)


def get_lesson_plans(subject: str, subtopic: str) -> Optional[Dict]:
    """Load lesson plans for a specific subject/subtopic."""
    data_service = get_data_service()
    lesson_data = data_service.data_loader.load_lesson_plans(subject, subtopic)
    return lesson_data.get("lessons", {}) if lesson_data else {}


def get_video_data(subject: str, subtopic: str) -> Optional[Dict]:
    """Load video data for a specific subject/subtopic."""
    data_service = get_data_service()
    videos_data = data_service.data_loader.load_videos(subject, subtopic)
    return videos_data.get("videos", {}) if videos_data else {}


# ============================================================================
# MAIN APPLICATION ROUTES
# ============================================================================


@main_bp.route("/")
def subject_selection():
    """New home page showing all available subjects."""
    try:
        data_service = get_data_service()
        subjects = data_service.discover_subjects()

        # Calculate stats for each subject
        for subject_id, subject_info in subjects.items():
            subject_config = data_service.load_subject_config(subject_id)

            if subject_config and "subtopics" in subject_config:
                subtopics = subject_config["subtopics"]
                total_lessons = 0
                total_videos = 0
                total_questions = 0

                for subtopic_id in subtopics.keys():
                    # Count lessons
                    lessons = get_lesson_plans(subject_id, subtopic_id)
                    total_lessons += len(lessons) if lessons else 0

                    # Count videos
                    videos = get_video_data(subject_id, subtopic_id)
                    if videos and "videos" in videos:
                        total_videos += len(videos["videos"])

                    # Count questions
                    quiz_data = get_quiz_data(subject_id, subtopic_id)
                    total_questions += len(quiz_data) if quiz_data else 0

                subject_info["stats"] = {
                    "lessons": total_lessons,
                    "videos": total_videos,
                    "questions": total_questions,
                    "subtopics": len(subtopics),
                }
            else:
                subject_info["stats"] = {
                    "lessons": 0,
                    "videos": 0,
                    "questions": 0,
                    "subtopics": 0,
                }

        return render_template("subject_selection.html", subjects=subjects)

    except Exception as e:
        print(f"Error loading subjects: {e}")
        return render_template("subject_selection.html", subjects={})


@main_bp.route("/subjects/<subject>")
def subject_page(subject):
    """Display subtopics for a specific subject."""
    try:
        data_service = get_data_service()
        progress_service = get_progress_service()

        # Load subject configuration and info
        subject_config = data_service.load_subject_config(subject)
        subject_info = data_service.load_subject_info(subject)

        if not subject_config or not subject_info:
            print(f"Subject data not found for: {subject}")
            return redirect(url_for("main.subject_selection"))

        subtopics = subject_config.get("subtopics", {})

        # Calculate actual counts for each subtopic by checking the files
        for subtopic_id, subtopic_data in subtopics.items():
            try:
                # Count quiz questions
                quiz_data = get_quiz_data(subject, subtopic_id)
                question_count = len(quiz_data) if quiz_data else 0

                # Count lesson plans
                lesson_plans = get_lesson_plans(subject, subtopic_id)
                lesson_count = len(lesson_plans) if lesson_plans else 0

                # Count videos
                video_data = get_video_data(subject, subtopic_id)
                video_count = len(video_data) if video_data else 0

                # Update subtopic data with actual counts
                subtopic_data["question_count"] = question_count
                subtopic_data["lesson_count"] = lesson_count
                subtopic_data["video_count"] = video_count

                # Get progress information
                progress_stats = progress_service.check_subtopic_progress(
                    subject, subtopic_id, lesson_count, video_count
                )
                subtopic_data["progress"] = progress_stats

            except Exception as e:
                print(f"Error processing subtopic {subtopic_id}: {e}")
                subtopic_data["question_count"] = 0
                subtopic_data["lesson_count"] = 0
                subtopic_data["video_count"] = 0
                subtopic_data["progress"] = {
                    "overall": {"completion_percentage": 0, "is_complete": False}
                }

        return render_template(
            "python_subject.html",
            subject=subject,
            subject_info=subject_info,
            subtopics=subtopics,
        )

    except Exception as e:
        print(f"Error loading subject page: {e}")
        return redirect(url_for("main.subject_selection"))


@main_bp.route("/python")
def python_subject_page():
    """Direct route to Python subject - for backward compatibility."""
    return redirect(url_for("main.subject_page", subject="python"))


# ============================================================================
# QUIZ ROUTES
# ============================================================================


@main_bp.route("/quiz/<subject>/<subtopic>")
def quiz_page(subject, subtopic):
    """Serves the initial quiz for any subject/subtopic."""
    try:
        data_service = get_data_service()
        progress_service = get_progress_service()

        # Validate that the subject/subtopic exists
        if not data_service.validate_subject_subtopic(subject, subtopic):
            return (
                f"Error: Subject '{subject}' with subtopic '{subtopic}' not found.",
                404,
            )

        # Clear previous session data for this subject/subtopic
        progress_service.clear_session_data(subject, subtopic)
        progress_service.reset_quiz_context()

        # Load quiz data
        quiz_questions = get_quiz_data(subject, subtopic)
        quiz_title = data_service.get_quiz_title(subject, subtopic)

        if not quiz_questions:
            return f"Error: No quiz questions found for {subject}/{subtopic}.", 404

        # Set session data for quiz
        progress_service.set_quiz_session_data(
            subject, subtopic, "initial", quiz_questions
        )
        progress_service.clear_remedial_quiz_data(subject, subtopic)

        return render_template(
            "quiz.html",
            questions=quiz_questions,
            quiz_title=quiz_title,
            admin_override=progress_service.get_admin_override_status(),
        )

    except Exception as e:
        print(f"Error loading quiz: {e}")
        return f"Error loading quiz: {e}", 500


@main_bp.route("/analyze", methods=["POST"])
def analyze_quiz():
    """Analyze quiz results and provide recommendations."""
    try:
        progress_service = get_progress_service()
        ai_service = get_ai_service()

        payload = request.get_json(silent=True) or {}
        raw_answers = payload.get("answers") or {}
        if not isinstance(raw_answers, dict):
            raw_answers = {}

        current_subject = session.get("current_subject")
        current_subtopic = session.get("current_subtopic")

        if not current_subject or not current_subtopic:
            return "Error: No active quiz session found.", 400

        quiz_session = progress_service.get_quiz_session_data(
            current_subject, current_subtopic
        )
        questions = quiz_session.get("questions", []) or []

        if not questions:
            return "Error: No quiz questions found in session.", 400

        answers: List[str] = []
        for index in range(len(questions)):
            answers.append(str(raw_answers.get(f"q{index}", "")).strip())

        analysis_result = ai_service.analyze_quiz_performance(
            questions, answers, current_subject, current_subtopic
        )

        stored_analysis = progress_service.store_quiz_analysis(
            current_subject, current_subtopic, analysis_result
        )
        weak_topic_candidates = (
            stored_analysis.get("weak_tags")
            or stored_analysis.get("weak_topics")
            or stored_analysis.get("missed_tags")
            or stored_analysis.get("weak_areas")
            or []
        )

        if isinstance(weak_topic_candidates, str):
            weak_topic_candidates = [weak_topic_candidates]

        progress_service.set_weak_topics(
            current_subject, current_subtopic, weak_topic_candidates
        )

        session["quiz_analysis"] = stored_analysis
        session["quiz_answers"] = answers

        return jsonify({"success": True, "analysis": stored_analysis})

    except Exception as e:
        print(f"Error analyzing quiz: {e}")
        return f"Error analyzing quiz: {e}", 500
@main_bp.route("/results")
def show_results_page():
    """Display quiz results page with personalized learning recommendations."""
    try:
        data_service = get_data_service()
        progress_service = get_progress_service()
        ai_service = get_ai_service()

        # Get analysis from session
        analysis = session.get("quiz_analysis")
        answers = session.get("quiz_answers")
        current_subject = session.get("current_subject")
        current_subtopic = session.get("current_subtopic")

        if not analysis and current_subject and current_subtopic:
            analysis = progress_service.get_quiz_analysis(current_subject, current_subtopic)
            if analysis:
                session["quiz_analysis"] = analysis

        if not analysis or not current_subject or not current_subtopic:
            return redirect(url_for("main.subject_selection"))

        answers = answers or []

        # Prepare remedial lesson and video maps based on analysis tags
        lesson_plan_map = {}
        video_map = {}

        topics_from_analysis = (
            analysis.get("weak_tags")
            or analysis.get("weak_topics")
            or analysis.get("weak_areas")
            or []
        )

        # Ensure unique order-preserved topics
        normalized_topics = []
        seen_topics = set()
        for topic in topics_from_analysis:
            if not topic:
                continue
            normalized = topic.strip()
            key = normalized.lower()
            if key in seen_topics:
                continue
            seen_topics.add(key)
            normalized_topics.append(normalized)

        # Gather lessons for the current subject/subtopic
        lessons_payload = (
            data_service.data_loader.load_lesson_plans(current_subject, current_subtopic)
            or {}
        )
        raw_lessons = lessons_payload.get("lessons", {})
        lesson_list: List[Dict[str, Any]] = []

        if isinstance(raw_lessons, dict):
            lesson_list = list(raw_lessons.values())
        elif isinstance(raw_lessons, list):
            lesson_list = raw_lessons

        for topic in normalized_topics:
            match = None
            topic_lower = topic.lower()
            for lesson in lesson_list:
                lesson_tags = [tag.lower() for tag in lesson.get("tags", [])]
                if topic_lower in lesson_tags:
                    match = lesson
                    break

            if not match and lesson_list:
                # Fallback to the first lesson if no specific tag match
                match = lesson_list[0]

            if match:
                # Include a shallow copy to avoid mutating original data
                lesson_plan_map[topic] = {
                    **match,
                    "subject": current_subject,
                    "subtopic": current_subtopic,
                }

        # Get video data for mapping
        video_data = get_video_data(current_subject, current_subtopic)
        if video_data and isinstance(video_data, dict):
            video_map = video_data.get("videos", {}) or {}

        # Get video recommendations if AI is available
        video_recommendations = []
        if ai_service.is_available():
            video_data = get_video_data(current_subject, current_subtopic)
            if video_data and "videos" in video_data:
                weak_areas = analysis.get("weak_areas", [])
                video_recommendations = ai_service.recommend_videos(
                    current_subject, current_subtopic, weak_areas, video_data["videos"]
                )

        # Determine if remedial quiz should be offered
        score_percentage = analysis.get("score", {}).get("percentage", 0)
        show_remedial = score_percentage < 70  # Threshold for remedial quiz

        return render_template(
            "results.html",
            analysis=analysis,
            ANALYSIS_RESULTS=analysis,
            answers=answers,
            subject=current_subject,
            subtopic=current_subtopic,
            CURRENT_SUBJECT=current_subject,
            CURRENT_SUBTOPIC=current_subtopic,
            LESSON_PLANS=lesson_plan_map,
            VIDEO_DATA=video_map,
            video_recommendations=video_recommendations,
            show_remedial=show_remedial,
            admin_override=session.get("admin_override", False),
            is_admin=session.get("admin_override", False),
            quiz_generation_error=None,
        )

    except Exception as e:
        print(f"Error displaying results: {e}")
        return redirect(url_for("main.subject_selection"))


@main_bp.route("/generate_remedial_quiz")
def generate_remedial_quiz():
    """Generate a remedial quiz based on previous performance."""
    try:
        data_service = get_data_service()
        progress_service = get_progress_service()

        current_subject = session.get("current_subject")
        current_subtopic = session.get("current_subtopic")

        if not current_subject or not current_subtopic:
            return jsonify({"success": False, "error": "Error: No active quiz session."}), 400

        weak_topics = progress_service.get_weak_topics(current_subject, current_subtopic)

        if not weak_topics:
            analysis = progress_service.get_quiz_analysis(current_subject, current_subtopic) or session.get("quiz_analysis", {}) or {}
            fallback_topics = (
                analysis.get("weak_tags")
                or analysis.get("weak_topics")
                or analysis.get("missed_tags")
                or analysis.get("weak_areas")
                or []
            )
            if isinstance(fallback_topics, list):
                weak_topics = [str(topic) for topic in fallback_topics if isinstance(topic, str)]
            elif isinstance(fallback_topics, str):
                weak_topics = [fallback_topics]

        weak_topics = [topic for topic in weak_topics if isinstance(topic, str) and topic.strip()]

        if not weak_topics:
            return jsonify({
                "success": False,
                "error": "No weak topics identified; remedial quiz not required.",
            }), 400

        question_pool = data_service.get_question_pool_questions(current_subject, current_subtopic) or []

        if not question_pool:
            return jsonify({
                "success": False,
                "error": "No question pool available for remedial quiz.",
            }), 404

        target_tags = {topic.strip().lower() for topic in weak_topics}
        remedial_questions = []
        seen_identifiers = set()

        for question in question_pool:
            question_tags_raw = question.get("tags", [])
            question_tags = [
                str(tag).strip().lower()
                for tag in question_tags_raw
                if isinstance(tag, str) and tag.strip()
            ]

            if not question_tags:
                continue

            if target_tags.intersection(question_tags):
                identifier = question.get("id") or question.get("question")
                if identifier and identifier not in seen_identifiers:
                    remedial_questions.append(question)
                    seen_identifiers.add(identifier)

        if not remedial_questions:
            return jsonify({
                "success": False,
                "error": "We couldn't find follow-up questions for your weak topics. Please review the materials and try again.",
            }), 404

        progress_service.set_remedial_quiz_data(
            current_subject, current_subtopic, remedial_questions, weak_topics
        )

        return jsonify(
            {
                "success": True,
                "question_count": len(remedial_questions),
                "redirect_url": url_for("main.take_remedial_quiz_page"),
            }
        )

    except Exception as e:
        print(f"Error generating remedial quiz: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
@main_bp.route("/take_remedial_quiz")
def take_remedial_quiz_page():
    """Page for taking the remedial quiz."""
    try:
        progress_service = get_progress_service()

        current_subject = session.get("current_subject")
        current_subtopic = session.get("current_subtopic")

        if not current_subject or not current_subtopic:
            return redirect(url_for("main.subject_selection"))

        remedial_questions = progress_service.get_remedial_quiz_questions(
            current_subject, current_subtopic
        )

        if not remedial_questions:
            return redirect(url_for("main.show_results_page"))

        quiz_title = (
            f"Remedial Quiz - {current_subject.title()} {current_subtopic.title()}"
        )

        return render_template(
            "quiz.html",
            questions=remedial_questions,
            quiz_title=quiz_title,
            is_remedial=True,
            admin_override=progress_service.get_admin_override_status(),
        )

    except Exception as e:
        print(f"Error loading remedial quiz: {e}")
        return redirect(url_for("main.subject_selection"))
