"""Test the Adaptavist module."""
import json
from unittest.mock import patch

from adaptavist import Adaptavist

from . import load_fixture


class TestAdaptavist:

    _jira_url = "mock://jira"
    _adaptavist_api_url = f"{_jira_url}/rest/atm/1.0"

    def test_get_users(self, requests_mock):
        requests_mock.get(f"{TestAdaptavist._jira_url}/rest/api/2/user/search?username=.&startAt=0&maxResults=200", text=load_fixture("get_users.json"))
        requests_mock.get(f"{TestAdaptavist._jira_url}/rest/api/2/user/search?username=.&startAt=1&maxResults=200", text="[]")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")
        users = adaptavist.get_users()
        assert users == ["Testuser"]

    def test_get_projects(self, requests_mock):
        requests_mock.get(f"{TestAdaptavist._jira_url}/rest/tests/1.0/project", text=load_fixture("get_projects.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")
        projects = adaptavist.get_projects()
        assert projects[0]["id"] == 10000

    def test_get_environments(self, requests_mock):
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/environments?projectKey=JQA", text=load_fixture("get_environments.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")
        envirenment = adaptavist.get_environments(project_key="JQA")
        assert envirenment[0]["id"] == 100

    def test_create_environment(self, requests_mock):
        requests_mock.post(f"{TestAdaptavist._adaptavist_api_url}/environments", text=load_fixture("create_environment.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")
        envirenment = adaptavist.create_environment(project_key="TEST", environment_name="Test environment", description="Cool new environment for testing.")
        assert envirenment == 37

    def test_get_folders(self, requests_mock):
        with patch("adaptavist.Adaptavist.get_projects", return_value=json.loads(load_fixture("get_projects.json"))):
            requests_mock.get(f"{TestAdaptavist._jira_url}/rest/tests/1.0/project/10000/foldertree/testcase?startAt=0&maxResults=200", text=load_fixture("get_folders.json"))
            adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")
            folders = adaptavist.get_folders(project_key="TEST", folder_type="TEST_CASE")
        assert folders == ["/", "/Test folder"]

    def test_create_folder(self, requests_mock):
        requests_mock.post(f"{TestAdaptavist._adaptavist_api_url}/folder", text=load_fixture("create_folder.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")
        folders = adaptavist.create_folder(project_key="TEST", folder_type="TEST_CASE", folder_name="Test folder")
        assert folders == 123

    def test_get_test_case(self, requests_mock):
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testcase/JQA-T123", text=load_fixture("get_test_case.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")
        test_case = adaptavist.get_test_case(test_case_key="JQA-T123")
        assert test_case["key"] == "JQA-T123"

    def test_get_test_cases(self, requests_mock):
        'mock://jira/rest/atm/1.0/'
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testcase/search?query=folder+%3C%3D+%22%2F%22&startAt=0", text=load_fixture("get_test_cases.json"))
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testcase/search?query=folder+%3C%3D+%22%2F%22&startAt=1", text="[]")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")
        test_cases = adaptavist.get_test_cases()
        assert test_cases[0]["key"] == "JQA-T123"

    def test_create_test_case(self, requests_mock):
        with patch("adaptavist.Adaptavist.get_folders", return_value=["/", "/Test folder"]):
            requests_mock.post(f"{TestAdaptavist._adaptavist_api_url}/testcase", text=load_fixture("create_test_case.json"))
            adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")
            test_case = adaptavist.create_test_case(project_key="JQA", test_case_name="Ensure the axial-flow pump is enabled")
        assert test_case == "JQA-T123"