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
from typing import Dict, List, Optional

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

        # Load quiz data
        quiz_questions = get_quiz_data(subject, subtopic)
        quiz_title = data_service.get_quiz_title(subject, subtopic)

        if not quiz_questions:
            return f"Error: No quiz questions found for {subject}/{subtopic}.", 404

        # Set session data for quiz
        progress_service.set_quiz_session_data(
            subject, subtopic, "initial", quiz_questions
        )

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
        data_service = get_data_service()
        progress_service = get_progress_service()
        ai_service = get_ai_service()

        # Get form data
        answers = []
        question_count = 0

        # Extract answers from form
        for key in request.form.keys():
            if key.startswith("q"):
                question_count += 1
                answers.append(request.form[key])

        # Get current session data
        current_subject = session.get("current_subject")
        current_subtopic = session.get("current_subtopic")

        if not current_subject or not current_subtopic:
            return "Error: No active quiz session found.", 400

        # Get session quiz data
        quiz_session = progress_service.get_quiz_session_data(
            current_subject, current_subtopic
        )
        questions = quiz_session.get("questions", [])

        if not questions:
            return "Error: No quiz questions found in session.", 400

        # Analyze with AI service
        analysis_result = ai_service.analyze_quiz_performance(
            questions, answers, current_subject, current_subtopic
        )

        # Store results in session for results page
        session["quiz_analysis"] = analysis_result
        session["quiz_answers"] = answers

        return redirect(url_for("main.show_results_page"))

    except Exception as e:
        print(f"Error analyzing quiz: {e}")
        return f"Error analyzing quiz: {e}", 500


@main_bp.route("/results")
def show_results_page():
    """Display quiz results page with personalized learning recommendations."""
    try:
        data_service = get_data_service()
        ai_service = get_ai_service()

        # Get analysis from session
        analysis = session.get("quiz_analysis")
        answers = session.get("quiz_answers")
        current_subject = session.get("current_subject")
        current_subtopic = session.get("current_subtopic")

        if not analysis or not current_subject or not current_subtopic:
            return redirect(url_for("main.subject_selection"))

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
            answers=answers,
            subject=current_subject,
            subtopic=current_subtopic,
            video_recommendations=video_recommendations,
            show_remedial=show_remedial,
            admin_override=session.get("admin_override", False),
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
        ai_service = get_ai_service()

        current_subject = session.get("current_subject")
        current_subtopic = session.get("current_subtopic")

        if not current_subject or not current_subtopic:
            return "Error: No active quiz session.", 400

        # Get original quiz data and performance
        quiz_session = progress_service.get_quiz_session_data(
            current_subject, current_subtopic
        )
        original_questions = quiz_session.get("questions", [])
        answers = session.get("quiz_answers", [])

        # Identify wrong answers
        wrong_indices = []
        for i, (question, answer) in enumerate(zip(original_questions, answers)):
            correct_answer = question.get("correct_answer", "")
            if answer.lower().strip() != correct_answer.lower().strip():
                wrong_indices.append(i)

        # Get question pool for remedial questions
        question_pool = data_service.get_question_pool_questions(
            current_subject, current_subtopic
        )

        if not question_pool:
            return "Error: No question pool available for remedial quiz.", 404

        # Generate remedial quiz
        remedial_questions = ai_service.generate_remedial_quiz(
            original_questions, wrong_indices, question_pool
        )

        if not remedial_questions:
            return "Error: Could not generate remedial quiz.", 500

        # Store remedial quiz in session
        session["remedial_questions"] = remedial_questions

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

        remedial_questions = session.get("remedial_questions")
        current_subject = session.get("current_subject")
        current_subtopic = session.get("current_subtopic")

        if not remedial_questions or not current_subject or not current_subtopic:
            return redirect(url_for("main.subject_selection"))

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
