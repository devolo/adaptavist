"""Test the Adaptavist module."""
import json
from io import BytesIO
from unittest.mock import mock_open, patch

from pytest import raises
from requests_mock import Mocker

from adaptavist import Adaptavist
from adaptavist.const import STATUS_FAIL, STATUS_PASS

from . import load_fixture


class TestAdaptavist:

    _jira_url = "mock://jira"
    _adaptavist_api_url = f"{_jira_url}/rest/atm/1.0"

    def test_get_users(self, requests_mock: Mocker):
        """Test getting all users."""
        requests_mock.get(f"{TestAdaptavist._jira_url}/rest/api/2/user/search?username=.&startAt=0&maxResults=200", text=load_fixture("get_users.json"))
        requests_mock.get(f"{TestAdaptavist._jira_url}/rest/api/2/user/search?username=.&startAt=1&maxResults=200", text="[]")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        users = adaptavist.get_users()
        assert users == ["Testuser"]

    def test_get_projects(self, requests_mock: Mocker):
        """Test getting all projects."""
        requests_mock.get(f"{TestAdaptavist._jira_url}/rest/tests/1.0/project", text=load_fixture("get_projects.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        projects = adaptavist.get_projects()
        assert projects[0]["id"] == 10000

    def test_get_environments(self, requests_mock: Mocker):
        """Test getting all environments of a project."""
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/environments?projectKey=JQA", text=load_fixture("get_environments.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        environment = adaptavist.get_environments(project_key="JQA")
        assert environment[0]["id"] == 100

    def test_create_environment(self, requests_mock: Mocker):
        """Test creating an environment for a project."""
        requests_mock.post(f"{TestAdaptavist._adaptavist_api_url}/environments", text=load_fixture("create_environment.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        environment = adaptavist.create_environment(project_key="TEST", environment_name="Test environment", description="Cool new environment for testing.")
        assert environment == 37

    def test_get_folders(self, requests_mock: Mocker):
        """Test getting all folders of a project."""
        requests_mock.get(f"{TestAdaptavist._jira_url}/rest/tests/1.0/project/10000/foldertree/testcase?startAt=0&maxResults=200",
                          text=load_fixture("get_folders.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_projects", return_value=json.loads(load_fixture("get_projects.json"))):
            folders = adaptavist.get_folders(project_key="TEST", folder_type="TEST_CASE")
            assert folders == ["/", "/Test folder"]

    def test_create_folder(self, requests_mock: Mocker):
        """Test creating a folder in a project."""
        requests_mock.post(f"{TestAdaptavist._adaptavist_api_url}/folder", text=load_fixture("create_folder.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_folders", return_value=["/"]):
            folders = adaptavist.create_folder(project_key="TEST", folder_type="TEST_CASE", folder_name="Test folder")
            assert folders == 123

        # Test that existing folders are not created twice
        with patch("adaptavist.Adaptavist.get_folders", return_value=["/", "/Test folder"]):
            assert adaptavist.create_folder(project_key="TEST", folder_type="TEST_CASE", folder_name="Test folder") is None

        # Test that the root folder is not created again
        with patch("adaptavist.Adaptavist.get_folders"):
            assert adaptavist.create_folder(project_key="TEST", folder_type="TEST_CASE", folder_name="/") is None

    def test_get_test_case(self, requests_mock: Mocker):
        """Test getting a single test case of a project."""
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testcase/JQA-T123", text=load_fixture("get_test_case.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        test_case = adaptavist.get_test_case(test_case_key="JQA-T123")
        assert test_case["key"] == "JQA-T123"

    def test_get_test_cases(self, requests_mock: Mocker):
        """Test getting all test cases of a project."""
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testcase/search?query=folder+%3C%3D+%22%2F%22&startAt=0",
                          text=load_fixture("get_test_cases.json"))
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testcase/search?query=folder+%3C%3D+%22%2F%22&startAt=1", text="[]")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        test_cases = adaptavist.get_test_cases()
        assert test_cases[0]["key"] == "JQA-T123"

    def test_create_test_case(self, requests_mock: Mocker):
        """Test creating a test case for a project."""
        requests_mock.post(f"{TestAdaptavist._adaptavist_api_url}/testcase", text=load_fixture("create_test_case.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.create_folder"):
            test_case = adaptavist.create_test_case(project_key="JQA", test_case_name="Ensure the axial-flow pump is enabled", folder="Test folder")
            assert test_case == "JQA-T123"

        # Test that folder is submitted as null if the root folder is chosen
        with patch("adaptavist.Adaptavist.create_folder"), \
             patch("adaptavist.Adaptavist._post") as post:
            adaptavist.create_test_case(project_key="JQA", test_case_name="Ensure the axial-flow pump is enabled")
            assert post.call_args_list[0][0][1]['folder'] is None

    def test_edit_test_case(self, requests_mock: Mocker):
        """Test editing a test case of a project."""
        requests_mock.put(f"{TestAdaptavist._adaptavist_api_url}/testcase/JQA-T123")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_test_case", return_value={"name": "Test case", "projectKey": "JQA"}), \
             patch("adaptavist.Adaptavist.create_folder"):
            assert adaptavist.edit_test_case(test_case_key="JQA-T123", folder="Test folder")

        # Test that folder is submitted as null if the root folder is chosen
        with patch("adaptavist.Adaptavist.get_test_case", return_value={"name": "Test case", "projectKey": "JQA"}), \
             patch("adaptavist.Adaptavist.create_folder"), \
             patch("adaptavist.Adaptavist._put") as put:
            assert adaptavist.edit_test_case(test_case_key="JQA-T123", folder="/")
            assert put.call_args_list[0][0][1]['folder'] is None

        # Test that existing labels are removed, if the list starts with "-"
        with patch("adaptavist.Adaptavist.get_test_case", return_value={"name": "Test case", "projectKey": "JQA", "labels": ["automated"]}), \
             patch("adaptavist.Adaptavist.create_folder"), \
             patch("adaptavist.Adaptavist._put") as put:
            assert adaptavist.edit_test_case(test_case_key="JQA-T123", folder="/", labels=["-", "tested"])
            assert put.call_args_list[0][0][1]['labels'] == ["tested"]

        # Test that existing custom fields are emptied, if the list starts with "-"
        with patch("adaptavist.Adaptavist.get_test_case", return_value={"name": "Test case", "projectKey": "JQA", "ci_server_url": ["mock://jenkins"]}), \
             patch("adaptavist.Adaptavist.create_folder"), \
             patch("adaptavist.Adaptavist._put") as put:
            assert adaptavist.edit_test_case(test_case_key="JQA-T123", folder="/", build_urls=["-", "mock://gitlab"])
            assert put.call_args_list[0][0][1]['customFields'] == {"ci_server_url": "mock://gitlab"}

    def test_delete_test_case(self, requests_mock: Mocker):
        """Test deleting a test case of a project."""
        requests_mock.delete(f"{TestAdaptavist._adaptavist_api_url}/testcase/JQA-T123")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        assert adaptavist.delete_test_case(test_case_key="JQA-T123")

    def test_get_test_case_links(self, requests_mock: Mocker):
        """Test getting a list of test cases linked to an issue."""
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/issuelink/JQA-1234/testcases", text=load_fixture("get_test_case_links.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        test_cases = adaptavist.get_test_case_links(issue_key="JQA-1234")
        assert test_cases[0]["key"] == "JQA-T123"

    def test_link_test_cases(self, requests_mock: Mocker):
        """Test linking an issue to test cases."""
        requests_mock.put(f"{TestAdaptavist._adaptavist_api_url}/testcase/JQA-T123")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_test_case", return_value={"name": "Test case", "projectKey": "JQA"}):
            assert adaptavist.link_test_cases(issue_key="JQA-123", test_case_keys=["JQA-T123"])

        # Test linking multiple test cases
        with patch("adaptavist.Adaptavist.get_test_case", return_value={"name": "Test case", "projectKey": "JQA"}), \
             patch("adaptavist.Adaptavist._put") as put:
            assert adaptavist.link_test_cases(issue_key="JQA-123", test_case_keys=["JQA-T123", "JQA-T124"])
            assert put.call_count == 2

        # Test that adding already existing issues do not trigger I/O
        with patch("adaptavist.Adaptavist.get_test_case", return_value={"name": "Test case", "projectKey": "JQA", "issueLinks": ["JQA-123"]}), \
             patch("adaptavist.Adaptavist._put") as put:
            assert adaptavist.link_test_cases(issue_key="JQA-123", test_case_keys=["JQA-T123"])
            assert put.assert_not_called

    def test_unlink_test_cases(self, requests_mock: Mocker):
        """Test unlinking an issue from a test cases."""
        requests_mock.put(f"{TestAdaptavist._adaptavist_api_url}/testcase/JQA-T123")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_test_case", return_value={"name": "Test case", "projectKey": "JQA"}):
            assert adaptavist.unlink_test_cases(issue_key="JQA-123", test_case_keys=["JQA-T123"])

        # Test unlinking multiple test cases
        # Actually, we are cheating here a bit: using link_test_cases the same issue cannot be linked twice.
        # But to trick how Python handles lists, we return the same issue twice in the patched return value.
        with patch("adaptavist.Adaptavist.get_test_case", return_value={"name": "Test case", "projectKey": "JQA", "issueLinks": ["JQA-123", "JQA-123"]}), \
             patch("adaptavist.Adaptavist._put") as put:
            assert adaptavist.unlink_test_cases(issue_key="JQA-123", test_case_keys=["JQA-T123", "JQA-T124"])
            assert put.call_count == 2

        # Test that not linked issues do not trigger I/O
        with patch("adaptavist.Adaptavist.get_test_case", return_value={"name": "Test case", "projectKey": "JQA", "issueLinks": ["JQA-124"]}), \
             patch("adaptavist.Adaptavist._put") as put:
            assert adaptavist.unlink_test_cases(issue_key="JQA-123", test_case_keys=["JQA-T123"])
            assert put.assert_not_called

    def test_get_test_plan(self, requests_mock: Mocker):
        """Test getting a test plan of a project."""
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testplan/JQA-P1234", text=load_fixture("get_test_plan.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        test_plan = adaptavist.get_test_plan(test_plan_key="JQA-P1234")
        assert test_plan["key"] == "JQA-P123"

    def test_get_test_plans(self, requests_mock: Mocker):
        """Test getting all test plans of a project."""
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testplan/search?query=folder+%3C%3D+%22%2F%22&startAt=0",
                          text=load_fixture("get_test_plans.json"))
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testplan/search?query=folder+%3C%3D+%22%2F%22&startAt=1", text="[]")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        test_plan = adaptavist.get_test_plans()
        assert test_plan[0]["key"] == "JQA-P123"

    def test_create_test_plan(self, requests_mock: Mocker):
        """Test creating a test plan for a project."""
        requests_mock.post(f"{TestAdaptavist._adaptavist_api_url}/testplan", text=load_fixture("create_test_plan.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.create_folder"):
            test_plan = adaptavist.create_test_plan(project_key="JQA", test_plan_name="Plan for a new version", folder="Test folder")
            assert test_plan == "JQA-P123"

        # Test that folder is submitted as null if the root folder is chosen
        with patch("adaptavist.Adaptavist.create_folder"), \
             patch("adaptavist.Adaptavist._post") as post:
            adaptavist.create_test_plan(project_key="JQA", test_plan_name="Plan for a new version")
            assert post.call_args_list[0][0][1]['folder'] is None

    def test_edit_test_plan(self, requests_mock: Mocker):
        """Test editing a test plan of a project."""
        requests_mock.put(f"{TestAdaptavist._adaptavist_api_url}/testplan/JQA-P123")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_test_plan", return_value={"name": "Test plan", "projectKey": "JQA"}), \
             patch("adaptavist.Adaptavist.create_folder"):
            assert adaptavist.edit_test_plan(test_plan_key="JQA-P123", folder="Test folder")

        # Test that folder is submitted as null if the root folder is chosen
        with patch("adaptavist.Adaptavist.get_test_plan", return_value={"name": "Test plan", "projectKey": "JQA"}), \
             patch("adaptavist.Adaptavist.create_folder"), \
             patch("adaptavist.Adaptavist._put") as put:
            assert adaptavist.edit_test_plan(test_plan_key="JQA-P123", folder="/")
            assert put.call_args_list[0][0][1]['folder'] is None

        # Test that existing labels are removed, if the list starts with "-"
        with patch("adaptavist.Adaptavist.get_test_plan", return_value={"name": "Test plan", "projectKey": "JQA", "labels": ["automated"]}), \
             patch("adaptavist.Adaptavist.create_folder"), \
             patch("adaptavist.Adaptavist._put") as put:
            assert adaptavist.edit_test_plan(test_plan_key="JQA-P123", folder="/", labels=["-", "tested"])
            assert put.call_args_list[0][0][1]['labels'] == ["tested"]

    def test_get_test_run(self, requests_mock: Mocker):
        """Test getting a test run of a project by its key."""
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testrun/JQA-R123", text=load_fixture("get_test_run.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        test_run = adaptavist.get_test_run(test_run_key="JQA-R123")
        assert test_run["key"] == "JQA-R123"

    def test_get_test_run_by_name(self, requests_mock: Mocker):
        """Test getting a test run of a project by its name."""
        requests_mock.get(
            f"{TestAdaptavist._jira_url}/rest/tests/1.0/testrun/search?startAt=0&maxResults=10000&query=testRun.name+%3D+%22Testplan%22&fields=id,key,name",
            text=load_fixture("get_test_run_by_name.json"))
        requests_mock.get(
            f"{TestAdaptavist._jira_url}/rest/tests/1.0/testrun/search?startAt=1&maxResults=10000&query=testRun.name+%3D+%22Testplan%22&fields=id,key,name",
            text='{"results":[]}')
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        test_run = adaptavist.get_test_run_by_name(test_run_name="Testplan")
        assert test_run["key"] == "JQA-R123"
        assert test_run["name"] == "Testplan"

    def test_get_test_runs(self, requests_mock: Mocker):
        """Test getting all test runs of a project."""
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testrun/search?query=folder+%3D+%22%2F%22&startAt=0", text=load_fixture("get_test_runs.json"))
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testrun/search?query=folder+%3D+%22%2F%22&startAt=1", text="[]")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        test_run = adaptavist.get_test_runs()
        assert test_run[0]["key"] == "JQA-R123"

    def test_get_test_run_links(self):
        """Test getting issues linked to a run of a project."""
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_test_runs", return_value=json.loads(load_fixture("get_test_runs.json"))):
            test_run = adaptavist.get_test_run_links(issue_key="JQA-123")
            assert test_run[0]["key"] == "JQA-R123"

    def test_create_test_run(self, requests_mock: Mocker):
        """Test creating a test run for a project."""
        requests_mock.post(f"{TestAdaptavist._adaptavist_api_url}/testrun", text=load_fixture("create_test_run.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.create_folder"):
            test_run = adaptavist.create_test_run(project_key="JQA", test_run_name="Run for a new version", folder="Test folder")
            assert test_run == "JQA-R123"

        # Test that folder is submitted as null if the root folder is chosen
        with patch("adaptavist.Adaptavist.create_folder"), \
             patch("adaptavist.Adaptavist._post") as post:
            adaptavist.create_test_run(project_key="JQA", test_run_name="Plan for a new version")
            assert post.call_args_list[0][0][1]['folder'] is None

    def test_clone_test_run(self):
        """Test cloning an existing test run."""
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_test_run", return_value=json.loads(load_fixture("get_test_run.json"))), \
             patch("adaptavist.Adaptavist.create_test_run", return_value="JQA-R124") as create_test_run, \
             patch("adaptavist.Adaptavist.get_test_plans", return_value=json.loads(load_fixture("get_test_plans.json"))), \
             patch("adaptavist.Adaptavist.edit_test_plan") as edit_test_plan:
            test_run = adaptavist.clone_test_run(test_run_key="JQA-R123", test_run_name="Cloned test case")
            assert test_run == "JQA-R124"
            assert create_test_run.call_args_list[0][1]["test_run_name"] == "Cloned test case"
            assert edit_test_plan.assert_called_once

        # Test that cloned test cases are only linked, if the original test case was linked to something
        with patch("adaptavist.Adaptavist.get_test_run", return_value=json.loads(load_fixture("get_test_run.json"))), \
             patch("adaptavist.Adaptavist.create_test_run", return_value="JQA-R124") as create_test_run, \
             patch("adaptavist.Adaptavist.get_test_plans", return_value=[]), \
             patch("adaptavist.Adaptavist.edit_test_plan") as edit_test_plan:
            test_run = adaptavist.clone_test_run(test_run_key="JQA-R123")
            assert test_run == "JQA-R124"
            assert edit_test_plan.assert_not_called

        # Test that cloned test append a suffix, if no name is given
        with patch("adaptavist.Adaptavist.get_test_run", return_value=json.loads(load_fixture("get_test_run.json"))), \
             patch("adaptavist.Adaptavist.create_test_run", return_value="JQA-R124") as create_test_run, \
             patch("adaptavist.Adaptavist.get_test_plans", return_value=[]), \
             patch("adaptavist.Adaptavist.edit_test_plan"):
            test_run = adaptavist.clone_test_run(test_run_key="JQA-R123")
            assert create_test_run.call_args_list[0][1]["test_run_name"] == "Full regression (cloned from JQA-R123)"

    def test_get_test_execution_results(self, requests_mock: Mocker):
        """Test getting all test execution results."""
        requests_mock.get(f"{TestAdaptavist._jira_url}/rest/tests/1.0/reports/testresults?startAt=0&maxResults=10000",
                          text=load_fixture("get_test_execution_results.json"))
        requests_mock.get(f"{TestAdaptavist._jira_url}/rest/tests/1.0/reports/testresults?startAt=1&maxResults=10000", text='{"results":[]}')
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        results = adaptavist.get_test_execution_results()
        assert results[0]["key"] == "JQA-E123"

    def test_get_test_results(self, requests_mock: Mocker):
        """Test getting test results of a test run."""
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testrun/JQA-T123/testresults", text=load_fixture("get_test_results.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        results = adaptavist.get_test_results(test_run_key="JQA-T123")
        assert results[0]["testCaseKey"] == "JQA-T123"

    def test_create_test_results(self, requests_mock: Mocker):
        """Test creating test results."""
        requests_mock.post(f"{TestAdaptavist._adaptavist_api_url}/testrun/JQA-R123/testresults", text=load_fixture("create_test_results.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_test_run", return_value=json.loads(load_fixture("get_test_run.json"))):
            assert adaptavist.create_test_results(test_run_key="JQA-R123", results=[{"status": "Fail", "testCaseKey": "JQA-T5678"}])

        # Test that executor and assignee are submitted as null if empty string is given
        with patch("adaptavist.Adaptavist.get_test_run", return_value=json.loads(load_fixture("get_test_run.json"))), \
             patch("adaptavist.Adaptavist._post") as post:
            adaptavist.create_test_results(test_run_key="JQA-R123", results=[{"status": "Fail", "testCaseKey": "JQA-T5678"}], assignee="", executor="")
            assert post.call_args_list[0][0][1][0]['assignedTo'] is None
            assert post.call_args_list[0][0][1][0]['executedBy'] is None

    def test_get_test_result(self):
        """Test getting a test result of a test run."""
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_test_results", return_value=json.loads(load_fixture("get_test_results.json"))):
            result = adaptavist.get_test_result(test_run_key="JQA-R123", test_case_key="JQA-T123")
            assert result["testCaseKey"] == "JQA-T123"

    def test_create_test_result(self, requests_mock: Mocker):
        """Test creating a test result."""
        requests_mock.post(f"{TestAdaptavist._adaptavist_api_url}/testrun/JQA-R123/testcase/JQA-T123/testresult", text=load_fixture("create_test_result.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        result = adaptavist.create_test_result(test_run_key="JQA-R123", test_case_key="JQA-T123", status=STATUS_PASS)
        assert result == 123

        # Test that executor and assignee are submitted as null if empty string is given
        with patch("adaptavist.Adaptavist._post") as post:
            adaptavist.create_test_result(test_run_key="JQA-R123", test_case_key="JQA-T123", status=STATUS_PASS, assignee="", executor="")
            assert post.call_args_list[0][0][1]["assignedTo"] is None
            assert post.call_args_list[0][0][1]["executedBy"] is None

        # Test that optional fields are send if set
        with patch("adaptavist.Adaptavist._post") as post:
            adaptavist.create_test_result(test_run_key="JQA-R123", test_case_key="JQA-T123", status=STATUS_PASS, execute_time=3, issue_links=["JQA-123"])
            assert post.call_args_list[0][0][1]["executionTime"] == 3000
            assert post.call_args_list[0][0][1]["issueLinks"] == ["JQA-123"]

        # Test that optional fields are not send if not set
        with patch("adaptavist.Adaptavist._post") as post:
            adaptavist.create_test_result(test_run_key="JQA-R123", test_case_key="JQA-T123", status=STATUS_PASS)
            assert not hasattr(post.call_args_list[0][0][1], "executionTime")
            assert not hasattr(post.call_args_list[0][0][1], "issueLinks")

    def test_edit_test_result_status(self, requests_mock: Mocker):
        """Test creating a test result."""
        requests_mock.put(f"{TestAdaptavist._adaptavist_api_url}/testrun/JQA-R123/testcase/JQA-T123/testresult")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        assert adaptavist.edit_test_result_status(test_run_key="JQA-R123", test_case_key="JQA-T123", status=STATUS_FAIL)

        # Test that executor and assignee are submitted as null if empty string is given
        with patch("adaptavist.Adaptavist._put") as put:
            adaptavist.edit_test_result_status(test_run_key="JQA-R123", test_case_key="JQA-T123", status=STATUS_FAIL, assignee="", executor="")
            assert put.call_args_list[0][0][1]["assignedTo"] is None
            assert put.call_args_list[0][0][1]["executedBy"] is None

        # Test that optional fields are send if set
        with patch("adaptavist.Adaptavist._put") as put:
            adaptavist.edit_test_result_status(test_run_key="JQA-R123",
                                               test_case_key="JQA-T123",
                                               status=STATUS_FAIL,
                                               environment="Firefox",
                                               comment="Test",
                                               execute_time=3,
                                               issue_links=["JQA-123"])
            assert put.call_args_list[0][0][1]["environment"] == "Firefox"
            assert put.call_args_list[0][0][1]["comment"] == "Test"
            assert put.call_args_list[0][0][1]["executionTime"] == 3000
            assert put.call_args_list[0][0][1]["issueLinks"] == ["JQA-123"]

        # Test that optional fields are not send if not set
        with patch("adaptavist.Adaptavist._put") as put:
            adaptavist.edit_test_result_status(test_run_key="JQA-R123", test_case_key="JQA-T123", status=STATUS_PASS)
            assert not hasattr(put.call_args_list[0][0][1], "environment")
            assert not hasattr(put.call_args_list[0][0][1], "comment")
            assert not hasattr(put.call_args_list[0][0][1], "executionTime")
            assert not hasattr(put.call_args_list[0][0][1], "issueLinks")

    def test_get_test_result_attachement(self, requests_mock: Mocker):
        """Test getting test result attachments."""
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testresult/123/attachments", text=load_fixture("get_test_result_attachments.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_test_result", return_value={"id": 123}):
            attachments = adaptavist.get_test_result_attachment(test_run_key="JQA-R123", test_case_key="JQA-T123")
            assert len(attachments) == 2

    def test_add_test_result_attachment(self):
        """Test adding an attachment."""
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_test_result", return_value={"id": 123}), \
             patch("builtins.open", mock_open()), \
             patch("requests_toolbelt.MultipartEncoder"), \
             patch("requests.post"):
            assert adaptavist.add_test_result_attachment(test_run_key="JQA-R123", test_case_key="JQA-T123", attachment="testfile", filename="testfile")

        # Test that a file name is needed, if no file handle is given
        with patch("adaptavist.Adaptavist.get_test_result", return_value={"id": 123}), \
             raises(SyntaxError):
            assert adaptavist.add_test_result_attachment(test_run_key="JQA-R123", test_case_key="JQA-T123", attachment="testfile")

        # Test that we can handle IO objects
        with patch("adaptavist.Adaptavist.get_test_result", return_value={"id": 123}), \
             patch("requests_toolbelt.MultipartEncoder"), \
             patch("requests.post"):
            attachment = BytesIO(b"Testdata")
            attachment.name = "testdata.txt"
            assert adaptavist.add_test_result_attachment(test_run_key="JQA-R123", test_case_key="JQA-T123", attachment=attachment)

    def test_edit_test_script_status(self, requests_mock: Mocker):
        """Test editing a test stript."""
        requests_mock.put(f"{TestAdaptavist._adaptavist_api_url}/testrun/JQA-R123/testcase/JQA-T123/testresult")
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_test_result",
                   return_value={
                       "id": 123, "status": STATUS_FAIL, "scriptResults": [{
                           "index": 0, "status": STATUS_FAIL
                       }]
                   }):
            assert adaptavist.edit_test_script_status(test_run_key="JQA-R123", test_case_key="JQA-T123", step=1, status=STATUS_PASS)

        # Test that executor and assignee are submitted as null if empty string is given
        with patch("adaptavist.Adaptavist.get_test_result", return_value={"id": 123, "status": STATUS_FAIL}), \
             patch("adaptavist.Adaptavist._put") as put:
            adaptavist.edit_test_script_status(test_run_key="JQA-R123", test_case_key="JQA-T123", step=1, status=STATUS_PASS, assignee="", executor="")
            assert put.call_args_list[0][0][1]["assignedTo"] is None
            assert put.call_args_list[0][0][1]["executedBy"] is None

        # Test that optional fields are send if set
        with patch("adaptavist.Adaptavist.get_test_result", return_value={"id": 123, "status": STATUS_FAIL}), \
             patch("adaptavist.Adaptavist._put") as put:
            adaptavist.edit_test_script_status(test_run_key="JQA-R123",
                                               test_case_key="JQA-T123",
                                               step=1,
                                               status=STATUS_PASS,
                                               environment="Firefox",
                                               assignee="Testuser",
                                               executor="Testuser")
            assert put.call_args_list[0][0][1]["environment"] == "Firefox"
            assert put.call_args_list[0][0][1]["assignedTo"] == "Testuser"
            assert put.call_args_list[0][0][1]["executedBy"] == "Testuser"

        # Test that optional fields are not send if not set
        with patch("adaptavist.Adaptavist.get_test_result", return_value={"id": 123, "status": STATUS_FAIL}), \
             patch("adaptavist.Adaptavist._put") as put:
            adaptavist.edit_test_script_status(test_run_key="JQA-R123", test_case_key="JQA-T123", step=1, status=STATUS_PASS)
            assert not hasattr(put.call_args_list[0][0][1], "environment")
            assert not hasattr(put.call_args_list[0][0][1], "assignedTo")
            assert not hasattr(put.call_args_list[0][0][1], "executedBy")

    def test_get_test_script_attachment(self, requests_mock: Mocker):
        """Test getting test script result attachments."""
        requests_mock.get(f"{TestAdaptavist._adaptavist_api_url}/testresult/123/step/0/attachments", text=load_fixture("get_test_result_attachments.json"))
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_test_result", return_value={"id": 123}):
            attachments = adaptavist.get_test_script_attachment(test_run_key="JQA-R123", test_case_key="JQA-T123", step=1)
            assert len(attachments) == 2

    def test_add_test_script_attachment(self):
        """Test adding an attachment."""
        adaptavist = Adaptavist(jira_server=TestAdaptavist._jira_url, jira_username="User", jira_password="Password")

        with patch("adaptavist.Adaptavist.get_test_result", return_value={"id": 123}), \
             patch("builtins.open", mock_open()), \
             patch("requests_toolbelt.MultipartEncoder"), \
             patch("requests.post"):
            assert adaptavist.add_test_script_attachment(test_run_key="JQA-R123", test_case_key="JQA-T123", step=1, attachment="testfile", filename="testfile")

        # Test that a file name is needed, if no file handle is given
        with patch("adaptavist.Adaptavist.get_test_result", return_value={"id": 123}), \
             raises(SyntaxError):
            assert adaptavist.add_test_script_attachment(test_run_key="JQA-R123", test_case_key="JQA-T123", step=1, attachment="testfile")

        # Test that we can handle IO objects
        with patch("adaptavist.Adaptavist.get_test_result", return_value={"id": 123}), \
             patch("requests_toolbelt.MultipartEncoder"), \
             patch("requests.post"):
            attachment = BytesIO(b"Testdata")
            attachment.name = "testdata.txt"
            assert adaptavist.add_test_script_attachment(test_run_key="JQA-R123", test_case_key="JQA-T123", step=1, attachment=attachment)
