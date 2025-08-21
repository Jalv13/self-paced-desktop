#!/usr/bin/env python3
"""
Simple test to verify the API endpoints work
"""
import json
import urllib.request
import urllib.parse


def test_api_endpoint():
    """Test the lessons API endpoint"""

    # Test data
    test_data = {
        "subject": "python",
        "tags": ["syntax", "function definition", "return values"],
    }

    # Convert to JSON
    data = json.dumps(test_data).encode("utf-8")

    # Create request
    req = urllib.request.Request(
        "http://127.0.0.1:5000/api/lessons/find-by-tags",
        data=data,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            print("API Response:")
            print(json.dumps(result, indent=2))
            return result
    except Exception as e:
        print(f"API Error: {e}")
        return None


if __name__ == "__main__":
    print("Testing API endpoint...")
    test_api_endpoint()
