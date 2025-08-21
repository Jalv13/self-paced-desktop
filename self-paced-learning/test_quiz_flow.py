#!/usr/bin/env python3
"""
Test script to simulate a quiz flow and check the results page
"""
import requests
import json

BASE_URL = "http://127.0.0.1:5000"


def test_quiz_flow():
    """Test the complete quiz flow"""
    session = requests.Session()

    print("1. Taking quiz...")
    # Go to the quiz page first to set up session
    quiz_response = session.get(f"{BASE_URL}/quiz/python/functions")
    print(f"Quiz page status: {quiz_response.status_code}")

    if quiz_response.status_code != 200:
        print("Failed to load quiz page")
        return

    print("2. Submitting quiz answers...")
    # Submit some answers to analyze
    test_answers = {
        "q0": "return",  # Some test answer
        "q1": "def function_name():",
        "q2": "Functions help organize code",
    }

    analyze_response = session.post(
        f"{BASE_URL}/analyze", json={"answers": test_answers}
    )

    print(f"Analysis status: {analyze_response.status_code}")
    if analyze_response.status_code == 200:
        analysis_data = analyze_response.json()
        print(f"Analysis result: {json.dumps(analysis_data, indent=2)}")
        print(f"Weak topics: {analysis_data.get('weak_topics', [])}")
    else:
        print(f"Analysis failed: {analyze_response.text}")
        return

    print("3. Accessing results page...")
    # Now go to results page
    results_response = session.get(f"{BASE_URL}/results")
    print(f"Results page status: {results_response.status_code}")

    if results_response.status_code == 200:
        # Check if we have the right content
        if "REMEDIAL_LESSON_PLANS" in results_response.text:
            print("✓ Results page loaded with lesson plans")
        else:
            print("✗ Results page missing lesson plans")

        if "VIDEO_DATA" in results_response.text:
            print("✓ Results page loaded with video data")
        else:
            print("✗ Results page missing video data")
    else:
        print(f"Results page failed: {results_response.text}")


if __name__ == "__main__":
    test_quiz_flow()
