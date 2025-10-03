"""AI Service Module

Handles all AI-powered features including OpenAI integration, quiz analysis,
and learning recommendations. Extracts AI logic from the main application routes.
"""

import openai
import os
from typing import Dict, List, Optional, Any
import json


class AIService:
    """Service class for handling AI-powered features."""

    def __init__(self):
        """Initialize the AI service with OpenAI configuration."""
        self.api_key = os.getenv("OPENAI_API_KEY")

        if self.api_key:
            openai.api_key = self.api_key
        else:
            print("Warning: OPENAI_API_KEY not set. AI features will not work.")

    def is_available(self) -> bool:
        """Check if AI service is available (API key configured)."""
        return self.api_key is not None

    # ============================================================================
    # CORE AI API METHODS
    # ============================================================================

    def call_openai_api(self, prompt: str, model: str = "gpt-4") -> Optional[str]:
        """Helper function to call the OpenAI API."""
        if not self.is_available():
            return None

        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful educational assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2000,
                temperature=0.7,
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return None

    # ============================================================================
    # QUIZ ANALYSIS AND RECOMMENDATIONS
    # ============================================================================

    def analyze_quiz_performance(
        self, questions: List[Dict], answers: List[str], subject: str, subtopic: str
    ) -> Dict[str, Any]:
        """Analyze quiz performance and generate recommendations."""
        if not self.is_available():
            return self._get_fallback_analysis(questions, answers)

        try:
            # Calculate basic metrics
            total_questions = len(questions)
            correct_answers = 0
            incorrect_topics = []

            # Analyze each question
            for i, (question, answer) in enumerate(zip(questions, answers)):
                correct_answer = question.get("correct_answer", "")

                if answer.lower().strip() == correct_answer.lower().strip():
                    correct_answers += 1
                else:
                    # Track topics that need work
                    topic = question.get("topic", "General")
                    if topic not in incorrect_topics:
                        incorrect_topics.append(topic)

            score_percentage = (
                (correct_answers / total_questions) * 100 if total_questions > 0 else 0
            )

            # Generate AI-powered analysis
            analysis_prompt = self._create_analysis_prompt(
                questions,
                answers,
                subject,
                subtopic,
                score_percentage,
                incorrect_topics,
            )

            ai_analysis = self.call_openai_api(analysis_prompt)

            return {
                "score": {
                    "correct": correct_answers,
                    "total": total_questions,
                    "percentage": score_percentage,
                },
                "weak_areas": incorrect_topics,
                "ai_analysis": ai_analysis,
                "recommendations": self._generate_recommendations(
                    score_percentage, incorrect_topics, subject, subtopic
                ),
            }

        except Exception as e:
            print(f"Error analyzing quiz performance: {e}")
            return self._get_fallback_analysis(questions, answers)

    def _create_analysis_prompt(
        self,
        questions: List[Dict],
        answers: List[str],
        subject: str,
        subtopic: str,
        score: float,
        weak_areas: List[str],
    ) -> str:
        """Create a prompt for AI analysis of quiz performance."""
        prompt = f"""
Analyze a student's quiz performance for {subject} - {subtopic}.

Quiz Results:
- Score: {score:.1f}% ({len([a for a, q in zip(answers, questions) if a.lower().strip() == q.get('correct_answer', '').lower().strip()])} out of {len(questions)} correct)
- Weak areas: {', '.join(weak_areas) if weak_areas else 'None identified'}

Questions and Answers:
"""

        for i, (question, answer) in enumerate(zip(questions, answers)):
            correct = question.get("correct_answer", "")
            is_correct = answer.lower().strip() == correct.lower().strip()

            prompt += f"""
Q{i+1}: {question.get('question', '')}
Student Answer: {answer}
Correct Answer: {correct}
Result: {'+' if is_correct else '-'}

"""

        prompt += """
Provide a brief, encouraging analysis focusing on:
1. Strengths demonstrated
2. Specific areas for improvement
3. Study suggestions
4. Next steps for learning

Keep the response concise and student-friendly.
"""

        return prompt

    def _generate_recommendations(
        self, score: float, weak_areas: List[str], subject: str, subtopic: str
    ) -> List[str]:
        """Generate learning recommendations based on performance."""
        recommendations = []

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
        total_questions = len(questions)
        correct_answers = sum(
            1
            for i, (q, a) in enumerate(zip(questions, answers))
            if a.lower().strip() == q.get("correct_answer", "").lower().strip()
        )

        score_percentage = (
            (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        )

        return {
            "score": {
                "correct": correct_answers,
                "total": total_questions,
                "percentage": score_percentage,
            },
            "weak_areas": [],
            "ai_analysis": "AI analysis not available. Please review your answers and try again.",
            "recommendations": self._generate_recommendations(
                score_percentage, [], "", ""
            ),
        }

    # ============================================================================
    # VIDEO RECOMMENDATIONS
    # ============================================================================

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
            # If no weak areas, recommend all videos
            return available_videos

        # Simple keyword matching for video recommendations
        recommended = []

        for video in available_videos:
            video_title = video.get("title", "").lower()
            video_description = video.get("description", "").lower()
            video_tags = [tag.lower() for tag in video.get("tags", [])]

            # Check if video content matches weak areas
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

        return (
            recommended if recommended else available_videos[:3]
        )  # Fallback to first 3 videos

    # ============================================================================
    # REMEDIAL QUIZ GENERATION
    # ============================================================================

    def generate_remedial_quiz(
        self,
        original_questions: List[Dict],
        wrong_answers: List[int],
        question_pool: List[Dict],
    ) -> List[Dict]:
        """Generate a remedial quiz focusing on areas where student struggled."""
        if not question_pool:
            return []

        # Identify topics from wrong answers
        weak_topics = set()
        for wrong_index in wrong_answers:
            if wrong_index < len(original_questions):
                topic = original_questions[wrong_index].get("topic", "")
                if topic:
                    weak_topics.add(topic.lower())

        # Filter question pool for remedial topics
        remedial_questions = []

        for question in question_pool:
            question_topic = question.get("topic", "").lower()
            question_tags = [tag.lower() for tag in question.get("tags", [])]

            # Check if question matches weak topics
            if question_topic in weak_topics or any(
                tag in weak_topics for tag in question_tags
            ):
                remedial_questions.append(question)

        # If no specific matches, use random questions from pool
        if not remedial_questions:
            remedial_questions = question_pool[:5]  # Fallback to first 5 questions

        # Limit to reasonable number of questions
        return remedial_questions[: min(len(remedial_questions), 5)]

    # ============================================================================
    # CONTENT GENERATION HELPERS
    # ============================================================================

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

        for i, lesson in enumerate(
            current_lessons[:5]
        ):  # Limit to first 5 for prompt size
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
            "valid": True,  # Assume valid unless obvious issues
            "feedback": feedback,
            "suggestions": [],  # Could be parsed from feedback if needed
        }
