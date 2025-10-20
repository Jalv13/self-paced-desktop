"""Regression tests for the admin subtopic edit workflow."""

import os
import sys
import re
from html import unescape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402


def test_admin_overview_edit_link_uses_modal_workflow():
    """Ensure the overview edit link resolves to the modal-enabled subtopics page."""

    with app.test_client() as client:
        overview_response = client.get("/admin/overview/subtopics")
        assert overview_response.status_code == 200

        html = overview_response.get_data(as_text=True)
        match = re.search(
            r'href="([^"]+)"[^>]*>\s*<i[^>]*fa-pen[^>]*></i>\s*Edit',
            html,
            re.IGNORECASE | re.DOTALL,
        )

        assert match is not None, "Edit link not found on overview page"

        edit_href = unescape(match.group(1))

        edit_response = client.get(edit_href, follow_redirects=True)
        assert edit_response.status_code == 200
        assert edit_response.request.path == "/admin/subtopics"
        assert "subject=" in edit_response.request.full_path


def test_admin_legacy_edit_route_redirects_to_modal_workflow():
    """Legacy subtopic edit route should redirect into the modal workflow."""

    with app.test_client() as client:
        legacy_response = client.get(
            "/admin/subjects/python/functions", follow_redirects=True
        )

        assert legacy_response.status_code == 200
        assert legacy_response.request.path == "/admin/subtopics"
        assert "subject=python" in legacy_response.request.full_path
        assert "subtopic=functions" in legacy_response.request.full_path
