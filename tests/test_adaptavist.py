"""Test the Adaptavist module."""

from adaptavist import Adaptavist

from . import load_fixture


class TestAdaptavist:

    def test_get_users(self, requests_mock):
        requests_mock.get("mock://jira/rest/api/2/user/search?username=.&startAt=0&maxResults=200", text=load_fixture("get_users.json"))
        requests_mock.get("mock://jira/rest/api/2/user/search?username=.&startAt=1&maxResults=200", text="[]")
        adaptavist = Adaptavist(jira_server="mock://jira", jira_username="User", jira_password="Password")
        users = adaptavist.get_users()
        assert users == ["Testuser"]
