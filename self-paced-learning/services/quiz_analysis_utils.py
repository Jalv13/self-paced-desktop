"""Utility helpers for rule-based quiz analysis and scoring."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

_ALLOWED_TAG_CACHE: Dict[str, List[str]] = {}


def _get_allowed_tags(subject: str, data_service: Optional[Any]) -> List[str]:
    """Return allowed tags for a subject using a small in-memory cache."""
    if not subject:
        return []
    cache_key = subject.lower()
    if cache_key in _ALLOWED_TAG_CACHE:
        return _ALLOWED_TAG_CACHE[cache_key]
    if not data_service:
        return []
    try:
        tags = data_service.get_subject_allowed_tags(subject) or []
    except Exception:
        tags = []
    normalized = [str(tag).strip() for tag in tags if isinstance(tag, str) and str(tag).strip()]
    _ALLOWED_TAG_CACHE[cache_key] = normalized
    return normalized


def resolve_correct_answer(question: Dict[str, Any]) -> str:
    """Return the canonical correct answer text for a question."""
    if not isinstance(question, dict):
        return ""
    if "correct_answer" in question and question["correct_answer"] is not None:
        return str(question.get("correct_answer", ""))
    if "answer" in question and question["answer"] is not None:
        return str(question.get("answer", ""))
    answer_index = question.get("answer_index")
    options = question.get("options")
    if isinstance(answer_index, int) and isinstance(options, Sequence) and 0 <= answer_index < len(options):
        value = options[answer_index]
        if isinstance(value, dict):
            value = value.get("text") or value.get("value")
        return str(value) if value is not None else ""
    acceptable = question.get("acceptable_answers") or question.get("correct_answers")
    if isinstance(acceptable, (list, tuple)) and acceptable:
        return str(acceptable[0])
    return ""


def is_answer_correct(question: Dict[str, Any], user_answer: str) -> bool:
    """Return True if the supplied answer should be considered correct."""
    if not isinstance(question, dict):
        return False
    question_type = str(question.get("type", "multiple_choice")).strip().lower()
    answer_text = resolve_correct_answer(question)
    user_clean = (user_answer or "").strip()
    if not user_clean:
        return False
    if question_type == "multiple_choice":
        return user_clean == answer_text.strip()
    if question_type == "fill_in_the_blank":
        acceptable: List[str] = []
        if answer_text:
            acceptable.extend(
                [part.strip().lower() for part in answer_text.split(",") if part.strip()]
            )
        raw_list = question.get("correct_answers") or question.get("acceptable_answers")
        if isinstance(raw_list, (list, tuple)):
            acceptable.extend([str(item).strip().lower() for item in raw_list if str(item).strip()])
        return user_clean.lower() in acceptable if acceptable else False
    if question_type == "coding":
        # Coding questions require AI/manual review in basic flow
        return False
    return user_clean.lower() == answer_text.strip().lower()


def collect_question_tags(question: Dict[str, Any]) -> List[str]:
    """Gather all tags/topics defined on a question."""
    tags: List[str] = []
    if not isinstance(question, dict):
        return tags
    raw_tags = question.get("tags")
    if isinstance(raw_tags, list):
        tags.extend(str(tag) for tag in raw_tags if isinstance(tag, (str, int)))
    elif isinstance(raw_tags, (str, int)):
        tags.append(str(raw_tags))
    topic = question.get("topic")
    if isinstance(topic, list):
        tags.extend(str(tag) for tag in topic if isinstance(tag, (str, int)))
    elif isinstance(topic, (str, int)):
        tags.append(str(topic))
    return tags


def normalize_tags(tags: Iterable[str]) -> List[str]:
    """Normalize tags by trimming whitespace and removing duplicates."""
    normalized: List[str] = []
    seen = set()
    for tag in tags or []:
        if not isinstance(tag, str):
            continue
        cleaned = tag.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(cleaned)
    return normalized


def filter_allowed_tags(tags: Iterable[str], allowed_lookup: Dict[str, str]) -> List[str]:
    """Filter tags against allowed lookup, preserving order and casing."""
    if not allowed_lookup:
        return normalize_tags(tags)
    filtered: List[str] = []
    seen = set()
    for tag in tags or []:
        if not isinstance(tag, str):
            continue
        cleaned = tag.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key not in allowed_lookup or key in seen:
            continue
        seen.add(key)
        filtered.append(allowed_lookup[key])
    return filtered


def _apply_rule_based_topics(
    question: Dict[str, Any],
    is_correct: bool,
    detected_tags: List[str],
) -> List[str]:
    """Augment detected tags with rule-based fallbacks."""
    if is_correct:
        return detected_tags
    question_type = str(question.get("type", "")).strip().lower()
    enriched = list(detected_tags)
    if question_type == "coding":
        enriched.append("programming logic")
    difficulty = question.get("difficulty")
    if isinstance(difficulty, str) and difficulty.lower() == "advanced":
        enriched.append("advanced practice")
    return enriched


def _build_submission_detail(
    index: int,
    question: Dict[str, Any],
    user_answer: str,
    status: str,
    correct_answer: str,
) -> str:
    parts = [
        f"Question {index + 1} (Type: {str(question.get('type', 'multiple_choice')).title()}): {question.get('question', 'N/A')}",
        "Student's Answer:",
        "---",
        user_answer if user_answer else "[No answer provided]",
        "---",
    ]
    if correct_answer:
        parts.append(f"Correct Answer: {correct_answer}")
    parts.append(f"Status: {status}")
    return "\n".join(parts) + "\n"


def _generate_basic_feedback(score_percentage: int, weak_topics: List[str]) -> str:
    if score_percentage >= 85:
        base = "Excellent work! You're mastering this material."
    elif score_percentage >= 70:
        base = "Great job! A little more practice will make these concepts stick."
    elif score_percentage >= 50:
        base = "Good effort—target the topics below to boost your understanding."
    else:
        base = "Let's reinforce the fundamentals. Review the weak areas highlighted below."
    if weak_topics:
        topics_str = ", ".join(weak_topics[:5])
        return f"{base} Focus on: {topics_str}."
    return base


def compute_basic_quiz_analysis(
    questions: Sequence[Dict[str, Any]],
    answers: Sequence[str],
    subject: str,
    subtopic: str,
    data_service: Optional[Any] = None,
    include_submission_details: bool = True,
) -> Dict[str, Any]:
    """Compute rule-based quiz analysis and scoring."""
    total_questions = len(questions)
    normalized_answers = [str(answer) if answer is not None else "" for answer in answers]
    correct_answers = 0
    wrong_indices: List[int] = []
    wrong_tag_candidates: List[str] = []
    weak_topic_details: List[Dict[str, Any]] = []
    submission_details: List[str] = []

    for idx, question in enumerate(questions):
        user_answer = normalized_answers[idx] if idx < len(normalized_answers) else ""
        status = "Incorrect"
        if is_answer_correct(question, user_answer):
            status = "Correct"
            correct_answers += 1
        else:
            wrong_indices.append(idx)
            detected = collect_question_tags(question)
            enriched_tags = _apply_rule_based_topics(question, False, detected)
            wrong_tag_candidates.extend(enriched_tags)
            weak_topic_details.append(
                {
                    "question_index": idx,
                    "question": question.get("question", ""),
                    "tags": normalize_tags(enriched_tags),
                    "type": question.get("type", "multiple_choice"),
                }
            )
            if str(question.get("type", "")).strip().lower() == "coding" and not user_answer:
                weak_topic_details[-1]["notes"] = "No code submitted for review."
        if include_submission_details:
            correct_answer = resolve_correct_answer(question)
            submission_details.append(
                _build_submission_detail(idx, question, user_answer, status, correct_answer)
            )

    percentage = int(round((correct_answers / total_questions) * 100)) if total_questions else 0
    allowed_tags = _get_allowed_tags(subject, data_service)
    allowed_lookup = {str(tag).lower(): str(tag) for tag in allowed_tags}
    filtered_tags = filter_allowed_tags(wrong_tag_candidates, allowed_lookup)
    if not filtered_tags:
        filtered_tags = normalize_tags(wrong_tag_candidates)

    feedback_message = _generate_basic_feedback(percentage, filtered_tags)
    analysis_stage = "basic"

    analysis: Dict[str, Any] = {
        "score": {
            "correct": correct_answers,
            "total": total_questions,
            "percentage": percentage,
        },
        "weak_topics": filtered_tags,
        "weak_tags": filtered_tags,
        "weak_areas": filtered_tags,
        "feedback": feedback_message,
        "ai_analysis": "",
        "recommendations": [],
        "submission_details": submission_details if include_submission_details else [],
        "wrong_question_indices": wrong_indices,
        "allowed_tags": allowed_tags,
        "used_ai": False,
        "analysis_stage": analysis_stage,
        "basic_feedback": feedback_message,
        "rule_based_insights": weak_topic_details,
        "subject": subject,
        "subtopic": subtopic,
    }

    if include_submission_details:
        analysis["submission_preview"] = "".join(submission_details)[:500]

    return analysis
