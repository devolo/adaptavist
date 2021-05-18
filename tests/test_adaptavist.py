"""Test the Adaptavist module."""
import json
from unittest.mock import patch

from adaptavist import Adaptavist

from . import load_fixture


class TestAdaptavist:

    _jira_url = "mock://jira"
    _adaptavist_api_url = f"{_jira_url}/rest/atm/1.0"

    def test_get_users(self, requests_mock):
        """Test getting all users."""
        requests_mock.get(f"{TestAdaptavist._jira_url}/rest/api/2/user/search?username=.&startAt=0&maxResults=200", text=load_fixture("get_users.json"))
        requests_mock.get(f"{TestAdaptavist._jira_url}/rest/api/2/user/search?username=.&startAt=1&maxResults=200", text="[]")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        users = adaptavist.get_users()
        assert users == ["Testuser"]

    def test_get_projects(self, requests_mock):
        """Test getting all projects."""
        requests_mock.get(f"{TestAdaptavist._jira_url}/rest/tests/1.0/project", text=load_fixture("get_projects.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        projects = adaptavist.get_projects()
        assert projects[0]["id"] == 10000

    def test_get_environments(self, requests_mock):
        """Test getting all environments of a project."""
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/environments?projectKey=JQA", text=load_fixture("get_environments.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        envirenment = adaptavist.get_environments(project_key="JQA")
        assert envirenment[0]["id"] == 100

    def test_create_environment(self, requests_mock):
        """Test creating an environment for a project."""
        requests_mock.post(f"{TestAdaptavist._adaptavist_api_url}/environments", text=load_fixture("create_environment.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        envirenment = adaptavist.create_environment(project_key="TEST", environment_name="Test environment", description="Cool new environment for testing.")
        assert envirenment == 37

    def test_get_folders(self, requests_mock):
        """Test getting all folders of a project."""
        requests_mock.get(f"{TestAdaptavist._jira_url}/rest/tests/1.0/project/10000/foldertree/testcase?startAt=0&maxResults=200", text=load_fixture("get_folders.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_projects", return_value=json.loads(load_fixture("get_projects.json"))):
            folders = adaptavist.get_folders(project_key="TEST", folder_type="TEST_CASE")
            assert folders == ["/", "/Test folder"]

    def test_create_folder(self, requests_mock):
        """Test creating a folder in a project."""
        requests_mock.post(f"{TestAdaptavist._adaptavist_api_url}/folder", text=load_fixture("create_folder.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_folders", return_value=["/"]):
            folders = adaptavist.create_folder(project_key="TEST", folder_type="TEST_CASE", folder_name="Test folder")
            assert folders == 123

    def test_get_test_case(self, requests_mock):
        """Test getting a single test case of a project."""
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testcase/JQA-T123", text=load_fixture("get_test_case.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        test_case = adaptavist.get_test_case(test_case_key="JQA-T123")
        assert test_case["key"] == "JQA-T123"

    def test_get_test_cases(self, requests_mock):
        """Test getting a all test cases of a project."""
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testcase/search?query=folder+%3C%3D+%22%2F%22&startAt=0", text=load_fixture("get_test_cases.json"))
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testcase/search?query=folder+%3C%3D+%22%2F%22&startAt=1", text="[]")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        test_cases = adaptavist.get_test_cases()
        assert test_cases[0]["key"] == "JQA-T123"

    def test_create_test_case(self, requests_mock):
        """Test creating a test case for a project."""
        requests_mock.post(f"{TestAdaptavist._adaptavist_api_url}/testcase", text=load_fixture("create_test_case.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_folders", return_value=["/", "/Test folder"]):
            test_case = adaptavist.create_test_case(project_key="JQA", test_case_name="Ensure the axial-flow pump is enabled", folder="Test folder")
            assert test_case == "JQA-T123"

        # Test that folder is submitted as null if the root folder is chosen
        with patch("adaptavist.Adaptavist.get_folders", return_value=["/"]), \
             patch("adaptavist.Adaptavist._post") as post:
            adaptavist.create_test_case(project_key="JQA", test_case_name="Ensure the axial-flow pump is enabled")
            assert post.call_args.args[1]['folder'] is None

    def test_edit_test_case(self, requests_mock):
        """Test editing a test case of a project."""
        requests_mock.put(f"{TestAdaptavist._adaptavist_api_url}/testcase/JQA-T123")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_folders", return_value=["/", "/Test folder"]), \
             patch("adaptavist.Adaptavist.get_test_case", return_value={"name": "Test case", "projectKey": "JQA"}):
            assert adaptavist.edit_test_case(test_case_key="JQA-T123", folder="Test folder")

        # Test that folder is submitted as null if the root folder is chosen
        with patch("adaptavist.Adaptavist.get_folders", return_value=["/"]), \
             patch("adaptavist.Adaptavist.get_test_case", return_value={"name": "Test case", "projectKey": "JQA"}), \
             patch("adaptavist.Adaptavist._put") as put:
            assert adaptavist.edit_test_case(test_case_key="JQA-T123", folder="/")
            assert put.call_args.args[1]['folder'] is None

        # Test that existing labels are removed, if the list starts with "-"
        with patch("adaptavist.Adaptavist.get_folders", return_value=["/"]), \
             patch("adaptavist.Adaptavist.get_test_case", return_value={"name": "Test case", "projectKey": "JQA", "labels": ["automated"]}), \
             patch("adaptavist.Adaptavist._put") as put:
            assert adaptavist.edit_test_case(test_case_key="JQA-T123", folder="/", labels=["-", "tested"])
            assert put.call_args.args[1]['labels'] == ["tested"]

        # Test that existing custom fields are emptied, if the list starts with "-"
        with patch("adaptavist.Adaptavist.get_folders", return_value=["/"]), \
             patch("adaptavist.Adaptavist.get_test_case", return_value={"name": "Test case", "projectKey": "JQA", "ci_server_url": ["mock://jenkins"]}), \
             patch("adaptavist.Adaptavist._put") as put:
            assert adaptavist.edit_test_case(test_case_key="JQA-T123", folder="/", build_urls=["-", "mock://gitlab"])
            assert put.call_args.args[1]['customFields'] == {"ci_server_url": "mock://gitlab"}

    def test_delete_test_case(self, requests_mock):
        """Test deleting a test case of a project."""
        requests_mock.delete(f"{TestAdaptavist._adaptavist_api_url}/testcase/JQA-T123")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        assert adaptavist.delete_test_case(test_case_key="JQA-T123")

    def test_get_test_case_links(self, requests_mock):
        """Test getting a list of test cases linked to an issue."""
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/issuelink/JQA-1234/testcases", text=load_fixture("get_test_case_links.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        test_cases = adaptavist.get_test_case_links(issue_key="JQA-1234")
        assert test_cases[0]["key"] == "JQA-T123"
