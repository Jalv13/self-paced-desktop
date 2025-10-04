"""AI Service Module

Handles all AI-powered features including OpenAI integration, quiz analysis,
and learning recommendations. Extracts AI logic from the main application routes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional

import openai

from .quiz_analysis_utils import (
    compute_basic_quiz_analysis,
    filter_allowed_tags,
    normalize_tags,
)

try:
    from openai import OpenAI as OpenAIClient
except ImportError:  # pragma: no cover - optional dependency path
    OpenAIClient = None


class AIService:
    """Service class for handling AI-powered features."""

    def __init__(self) -> None:
        """Initialize the AI service with OpenAI configuration."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.default_model = os.getenv("OPENAI_MODEL", "gpt-4")
        self.client: Optional[Any] = None
        self._analysis_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()

        if self.api_key and OpenAIClient:
            try:
                self.client = OpenAIClient(api_key=self.api_key)
            except TypeError:
                self.client = OpenAIClient()  # type: ignore[call-arg]
            except Exception as exc:  # pragma: no cover - defensive log path
                print(f"Warning: failed to initialize OpenAI client: {exc}")
                self.client = None

        if self.api_key:
            try:
                openai.api_key = self.api_key
            except Exception:  # pragma: no cover - OpenAI import optional
                pass
        else:
            print("Warning: OPENAI_API_KEY not set. AI features will not work.")

    def is_available(self) -> bool:
        """Check if AI service is available (API key configured)."""
        return self.api_key is not None

    # =======================================================================
    # CORE AI API METHODS
    # =======================================================================

    def call_openai_api(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_message: Optional[str] = None,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        expect_json_output: bool = False,
        timeout: int = 15,
        max_attempts: int = 3,
    ) -> Optional[str]:
        """Helper function to call the OpenAI API with retries and timeouts."""
        if not self.is_available():
            return None

        messages = [
            {
                "role": "system",
                "content": system_message
                or "You are a helpful educational assistant.",
            },
            {"role": "user", "content": prompt},
        ]

        model_to_use = model or getattr(self, "default_model", "gpt-4")
        kwargs: Dict[str, Any] = {
            "model": model_to_use,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if expect_json_output:
            kwargs["response_format"] = {"type": "json_object"}

        kwargs_with_timeout = dict(kwargs)
        kwargs_with_timeout["request_timeout"] = timeout
        kwargs_with_timeout.setdefault("timeout", timeout)

        last_error: Optional[Exception] = None
        backoff_seconds = 1.0

        def _invoke(callable_obj, call_kwargs):
            try:
                return callable_obj(**call_kwargs)
            except TypeError:
                trimmed = {
                    k: v
                    for k, v in call_kwargs.items()
                    if k not in ("timeout", "request_timeout")
                }
                return callable_obj(**trimmed)

        for attempt in range(1, max_attempts + 1):
            if getattr(self, "client", None) and getattr(self.client, "chat", None):
                try:
                    response = _invoke(self.client.chat.completions.create, kwargs_with_timeout)
                    content = self._extract_content_from_response(response)
                    if content:
                        return content.strip()
                except Exception as exc:
                    last_error = exc

            for api_call in (
                lambda: _invoke(openai.ChatCompletion.create, kwargs_with_timeout),
                lambda: _invoke(openai.chat.completions.create, kwargs_with_timeout),
            ):
                try:
                    response = api_call()
                    content = self._extract_content_from_response(response)
                    if content:
                        return content.strip()
                except AttributeError as exc:
                    last_error = exc
                except Exception as exc:
                    last_error = exc

            if getattr(self, "client", None) and getattr(self.client, "responses", None):
                try:
                    prompt_text = "\n".join(
                        message["content"] for message in messages if message.get("content")
                    )
                    response_kwargs = {
                        "model": model_to_use,
                        "input": prompt_text,
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                        "timeout": timeout,
                    }
                    response = _invoke(self.client.responses.create, response_kwargs)
                    content = self._extract_content_from_response(response)
                    if content:
                        return content.strip()
                except Exception as exc:
                    last_error = exc

            if attempt < max_attempts:
                time.sleep(backoff_seconds)
                backoff_seconds *= 2

        if last_error:
            print(f"Error calling OpenAI API: {last_error}")
        return None

    def _extract_content_from_response(self, response: Any) -> Optional[str]:
        if not response:
            return None

        choices = getattr(response, "choices", None)
        if choices:
            first_choice = choices[0]
            message = getattr(first_choice, "message", None)
            if isinstance(message, dict):
                content = message.get("content")
            else:
                content = getattr(message, "content", None)
            text_value = self._flatten_content(content)
            if text_value:
                return text_value

            text_attr = getattr(first_choice, "text", None)
            if isinstance(text_attr, str):
                return text_attr

        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        output = getattr(response, "output", None)
        if isinstance(output, list) and output:
            content = getattr(output[0], "content", None)
            text_value = self._flatten_content(content)
            if text_value:
                return text_value

        data = getattr(response, "data", None)
        if isinstance(data, list) and data:
            message = getattr(data[0], "message", None)
            if message:
                text_value = self._flatten_content(getattr(message, "content", None))
                if text_value:
                    return text_value

        if isinstance(response, dict):
            choices = response.get("choices")
            if choices:
                choice0 = choices[0] if choices else None
                message = choice0.get("message") if isinstance(choice0, dict) else None
                text_value = self._flatten_content(message.get("content") if message else None)
                if text_value:
                    return text_value
        return None

    def _flatten_content(self, content: Any) -> Optional[str]:
        if not content:
            return None
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text_value = item.get("text")
                    if isinstance(text_value, str):
                        parts.append(text_value)
                    else:
                        content_value = item.get("content")
                        if isinstance(content_value, str):
                            parts.append(content_value)
            if parts:
                return "\n".join(part for part in parts if part)
        if isinstance(content, dict):
            text_value = content.get("text")
            if isinstance(text_value, str):
                return text_value
            content_value = content.get("content")
            if isinstance(content_value, str):
                return content_value
        return None

    # =======================================================================
    # QUIZ ANALYSIS AND RECOMMENDATIONS
    # =======================================================================

    def analyze_quiz_performance(
        self,
        questions: List[Dict],
        answers: List[str],
        subject: str,
        subtopic: str,
        base_analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze quiz performance and generate tag-aware recommendations."""
        from services import get_data_service

        data_service = get_data_service()
        if base_analysis is None:
            base_analysis = compute_basic_quiz_analysis(
                questions,
                answers,
                subject,
                subtopic,
                data_service=data_service,
                include_submission_details=True,
            )

        analysis = dict(base_analysis)
        analysis.setdefault("analysis_stage", "basic")
        analysis.setdefault("feedback", analysis.get("basic_feedback", ""))

        allowed_tags = analysis.get("allowed_tags") or data_service.get_subject_allowed_tags(subject)
        analysis["allowed_tags"] = allowed_tags or []
        allowed_lookup = {
            str(tag).lower(): str(tag) for tag in (allowed_tags or []) if isinstance(tag, str)
        }

        rule_based_insights = analysis.get("rule_based_insights") or []
        wrong_tag_candidates: List[str] = []
        for detail in rule_based_insights:
            tags = detail.get("tags") if isinstance(detail, dict) else None
            if isinstance(tags, list):
                wrong_tag_candidates.extend(
                    str(tag) for tag in tags if isinstance(tag, (str, int))
                )

        normalized_missed_tags = normalize_tags(wrong_tag_candidates)

        fallback_tags = analysis.get("weak_tags") or analysis.get("weak_topics") or []
        if not fallback_tags:
            fallback_tags = filter_allowed_tags(wrong_tag_candidates, allowed_lookup)
            if not fallback_tags:
                fallback_tags = normalized_missed_tags

        submission_details = analysis.get("submission_details") or []
        if not submission_details:
            submission_details = [
                "\n".join(
                    [
                        f"Question {idx + 1}: {question.get('question', 'N/A')}",
                        f"Answer Provided: {answers[idx] if idx < len(answers) else ''}",
                    ]
                )
                for idx, question in enumerate(questions)
            ]

        cache_key = self._build_cache_key(questions, answers, subject, subtopic)
        cached = self._get_cached_analysis(cache_key)
        if cached:
            merged = dict(analysis)
            merged.update({k: v for k, v in cached.items() if v is not None})
            return merged

        if not self.is_available():
            return analysis

        allowed_tags_str = json.dumps(analysis.get("allowed_tags") or [])
        prompt_parts = [
            "You are analyzing a student's quiz submission which includes multiple choice, fill-in-the-blank, and coding questions.",
            "Based on the incorrect answers and their submitted code, identify the concepts they are weak in.",
            f"You MUST choose the weak concepts from this predefined list ONLY: {allowed_tags_str}",
            "For coding questions, comment on syntax, logic, and understanding.",
            "Provide your analysis as a JSON object with keys 'detailed_feedback' and 'weak_concept_tags'.",
            f"Overall score: {analysis['score']['correct']}/{analysis['score']['total']} correct ({analysis['score']['percentage']}%).",
            "Here is the student's submission:",
            "--- START OF SUBMISSION ---",
            "".join(submission_details) if submission_details else "[No submission details available]",
            "--- END OF SUBMISSION ---",
        ]
        prompt = "\n".join(part for part in prompt_parts if part)

        ai_response = self.call_openai_api(
            prompt,
            model=getattr(self, "default_model", "gpt-4"),
            system_message=(
                "You are an expert instructor. Analyze quiz performance, classify errors against allowed topics, "
                "and provide supportive feedback."
            ),
            max_tokens=1200,
            temperature=0.1,
            expect_json_output=True,
        )

        analysis["raw_ai_response"] = ai_response
        analysis["missed_tags"] = normalized_missed_tags

        if ai_response:
            parsed_response = self._extract_json_object(ai_response)
            if parsed_response:
                candidate_tags = parsed_response.get("weak_concept_tags") or []
                if isinstance(candidate_tags, str):
                    candidate_tags = [candidate_tags]
                validated_tags = filter_allowed_tags(candidate_tags, allowed_lookup)
                if not validated_tags:
                    validated_tags = fallback_tags
                feedback = (
                    parsed_response.get("detailed_feedback")
                    or parsed_response.get("feedback")
                    or analysis.get("feedback")
                    or ""
                )
                analysis["weak_topics"] = validated_tags
                analysis["weak_tags"] = validated_tags
                analysis["weak_areas"] = validated_tags
                analysis["feedback"] = feedback
                analysis["ai_analysis"] = feedback
                analysis["used_ai"] = True
                analysis["analysis_stage"] = "enhanced"
            else:
                analysis["weak_topics"] = fallback_tags
                analysis["weak_tags"] = fallback_tags
                analysis["weak_areas"] = fallback_tags
        else:
            analysis["weak_topics"] = fallback_tags
            analysis["weak_tags"] = fallback_tags
            analysis["weak_areas"] = fallback_tags

        if not analysis.get("recommendations"):
            analysis["recommendations"] = self._generate_recommendations(
                analysis["score"]["percentage"],
                analysis.get("weak_topics", []),
                subject,
                subtopic,
            )

        if analysis.get("used_ai"):
            self._set_cached_analysis(
                cache_key,
                {
                    "weak_topics": analysis.get("weak_topics"),
                    "weak_tags": analysis.get("weak_tags"),
                    "weak_areas": analysis.get("weak_areas"),
                    "feedback": analysis.get("feedback"),
                    "ai_analysis": analysis.get("ai_analysis"),
                    "used_ai": analysis.get("used_ai"),
                    "analysis_stage": analysis.get("analysis_stage"),
                    "raw_ai_response": analysis.get("raw_ai_response"),
                },
            )

        return analysis

    def _build_cache_key(
        self,
        questions: List[Dict[str, Any]],
        answers: List[str],
        subject: str,
        subtopic: str,
    ) -> str:
        payload = {
            "subject": subject,
            "subtopic": subtopic,
            "questions": [
                question.get("id")
                or question.get("question_id")
                or question.get("question", str(index))
                for index, question in enumerate(questions)
            ],
            "answers": list(answers),
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha1(serialized.encode("utf-8")).hexdigest()

    def _get_cached_analysis(self, cache_key: str) -> Optional[Dict[str, Any]]:
        with self._cache_lock:
            return self._analysis_cache.get(cache_key)

    def _set_cached_analysis(self, cache_key: str, analysis: Dict[str, Any]) -> None:
        with self._cache_lock:
            self._analysis_cache[cache_key] = analysis

    def _extract_json_object(self, response_text: str) -> Optional[Dict[str, Any]]:
        if not response_text:
            return None
        stripped = response_text.strip()
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{[\s\S]*\}", stripped)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None

    def _generate_recommendations(
        self, score: float, weak_areas: List[str], subject: str, subtopic: str
    ) -> List[str]:
        """Generate learning recommendations based on performance."""
        recommendations: List[str] = []

        if score >= 80:
            recommendations.append(
                "Great job! You have a strong understanding of this topic."
            )
            recommendations.append("Consider advancing to more challenging topics.")
        elif score >= 60:
            recommendations.append(
                "Good progress! Focus on reviewing the areas you missed."
            )
            if weak_areas:
                recommendations.append(
                    f"Pay special attention to: {', '.join(weak_areas)}"
                )
        else:
            recommendations.append(
                "Consider reviewing the lesson materials before retaking the quiz."
            )
            recommendations.append(
                "Practice exercises might help strengthen your understanding."
            )
            if weak_areas:
                recommendations.append(f"Focus your study on: {', '.join(weak_areas)}")

        return recommendations

    def _get_fallback_analysis(
        self, questions: List[Dict], answers: List[str]
    ) -> Dict[str, Any]:
        """Provide fallback analysis when AI is not available."""
        basic = compute_basic_quiz_analysis(questions, answers, "", "", data_service=None)
        basic["feedback"] = (
            "AI analysis not available. Please review your answers and try again."
        )
        basic["ai_analysis"] = basic["feedback"]
        return basic

    # =======================================================================
    # VIDEO RECOMMENDATIONS
    # =======================================================================

    def recommend_videos(
        self,
        subject: str,
        subtopic: str,
        weak_areas: List[str],
        available_videos: List[Dict],
    ) -> List[Dict]:
        """Recommend videos based on weak areas and available content."""
        if not available_videos:
            return []

        if not weak_areas:
            return available_videos

        recommended = []
        for video in available_videos:
            video_title = video.get("title", "").lower()
            video_description = video.get("description", "").lower()
            video_tags = [tag.lower() for tag in video.get("tags", [])]

            for weak_area in weak_areas:
                weak_area_lower = weak_area.lower()
                if (
                    weak_area_lower in video_title
                    or weak_area_lower in video_description
                    or any(weak_area_lower in tag for tag in video_tags)
                ):
                    if video not in recommended:
                        recommended.append(video)
                    break

        return recommended if recommended else available_videos[:3]

    # =======================================================================
    # REMEDIAL QUIZ GENERATION
    # =======================================================================

    def generate_remedial_quiz(
        self,
        original_questions: List[Dict],
        wrong_answers: List[int],
        question_pool: List[Dict],
    ) -> List[Dict]:
        """Generate a remedial quiz focusing on areas where student struggled."""
        if not question_pool:
            return []

        weak_topics = set()
        for wrong_index in wrong_answers:
            if wrong_index < len(original_questions):
                tags = original_questions[wrong_index].get("tags", [])
                for tag in tags or []:
                    weak_topics.add(str(tag).lower())

        remedial_questions = []
        for question in question_pool:
            question_tags = [str(tag).lower() for tag in question.get("tags", [])]
            if weak_topics.intersection(question_tags):
                remedial_questions.append(question)

        if not remedial_questions:
            remedial_questions = question_pool[:5]

        return remedial_questions[: min(len(remedial_questions), 5)]

    # =======================================================================
    # CONTENT GENERATION HELPERS
    # =======================================================================

    def generate_lesson_suggestions(
        self, subject: str, subtopic: str, current_lessons: List[Dict]
    ) -> Optional[str]:
        """Generate suggestions for new lesson content."""
        if not self.is_available():
            return None

        prompt = f"""
Analyze the existing lessons for {subject} - {subtopic} and suggest improvements or additional content.

Existing Lessons:
"""

        for i, lesson in enumerate(current_lessons[:5]):
            prompt += f"{i+1}. {lesson.get('title', 'Untitled')}\n"

        prompt += """
Provide 3-5 specific suggestions for:
1. New lesson topics that would complement existing content
2. Improvements to existing lessons
3. Interactive exercises that could be added

Keep suggestions practical and educational.
"""

        return self.call_openai_api(prompt)

    def validate_question_quality(self, question_data: Dict) -> Dict[str, Any]:
        """Validate and provide feedback on question quality."""
        if not self.is_available():
            return {"valid": True, "suggestions": []}

        prompt = f"""
Evaluate this quiz question for quality, clarity, and educational value:

Question: {question_data.get('question', '')}
Options: {', '.join(question_data.get('options', []))}
Correct Answer: {question_data.get('correct_answer', '')}
Explanation: {question_data.get('explanation', 'None provided')}

Provide feedback on:
1. Question clarity
2. Answer options quality
3. Difficulty appropriateness
4. Suggestions for improvement

Respond with a brief assessment and specific recommendations.
"""

        feedback = self.call_openai_api(prompt)

        return {
            "valid": True,
            "feedback": feedback,
            "suggestions": [],
        }
