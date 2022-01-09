"""This module provides functionality for Adaptavist Test Management with Jira server interaction."""

import json
import logging
from typing import Any, BinaryIO, Dict, List, Optional, Union
from urllib.parse import quote_plus

import requests
import requests_toolbelt

from ._helper import build_folder_names, get_executor, raise_on_kwargs_not_empty, update_field, update_multiline_field
from .const import PRIORITY_NORMAL, STATUS_APPROVED, STATUS_NOT_EXECUTED, STEP_TYPE_BY_STEP, TEST_CASE, TEST_PLAN, TEST_RUN


class Adaptavist:
    """
    The Adaptavist class.
    Uses REST API of Adaptavist Test Management for Jira Server to provide its functionality.

    .. seealso:: https://docs.adaptavist.io/tm4j/server/api
    """

    def __init__(self, jira_server: str, jira_username: str, jira_password: str):
        """Construct a new Adaptavist instance."""

        self.jira_server = jira_server
        self.jira_username = jira_username

        self._adaptavist_api_url = self.jira_server + "/rest/atm/1.0"
        self._authentication = requests.auth.HTTPBasicAuth(self.jira_username, jira_password)
        self._headers = {"Accept": "application/json", "Content-type": "application/json"}
        self._logger = logging.getLogger(__name__)

    def get_users(self) -> List[str]:
        """
        Get a list of users known to Adaptavist/Jira.

        :returns: List of user keys
        """
        users: List[Dict[str, Any]] = []
        i = 0
        while True:
            request_url = f"{self.jira_server}/rest/api/2/user/search?username=.&startAt={i}&maxResults=200"
            self._logger.debug("Asking for 200 users starting at %i", i + 1)
            request = self._get(request_url)
            result = request.json() if request else []
            if not result:
                break
            users = [*users, *result]
            i += len(result)
        return [user["key"] for user in users]

    def get_projects(self) -> List[Dict[str, Any]]:
        """
        Get a list of projects known to Adaptavist/Jira.

        :returns: List of projects
        """
        request_url = f"{self.jira_server}/rest/tests/1.0/project"
        self._logger.debug("Asking for product list.")
        request = self._get(request_url)
        return [{"id": project["id"], "key": project["key"], "name": project["name"]} for project in request.json()] if request else []

    def get_environments(self, project_key: str) -> List[Dict[str, Any]]:
        """
        Get a list of environments matching the search mask.

        :param project_key: Project key to search for environments
        :returns: List of environments
        """
        request_url = f"{self._adaptavist_api_url}/environments?projectKey={quote_plus(project_key)}"
        self._logger.debug("Asking environments in project '%s'.", project_key)
        request = self._get(request_url)
        return request.json() if request else []

    def create_environment(self, project_key: str, environment_name: str, **kwargs: Any) -> Optional[int]:
        """
        Create a new environment.

        :param project_key: Project key of the environment ex. "TEST"
        :param environment_name: Name of the environment to be created
        :key description: Description of the environment
        :return: id of the environment created
        """
        description: str = kwargs.pop("description", "")
        raise_on_kwargs_not_empty(kwargs)

        request_url = f"{self._adaptavist_api_url}/environments"
        self._logger.debug("Creating environment '%s' in project '%s'", environment_name, project_key)
        request_data = {
            "projectKey": project_key,
            "name": environment_name,
            "description": description,
        }

        request = self._post(request_url, request_data)
        return request.json()["id"] if request else None

    def get_folders(self, project_key: str, folder_type: str) -> List[str]:
        """
        Get a list of folders.

        :param project_key: Project key to search for folders
        :param folder_type: Type of the folder ("TEST_CASE", "TEST_PLAN" or "TEST_RUN")
        :returns: List of folders
        """
        project_id: Optional[int] = next((project["id"] for project in self.get_projects() if project["key"] == project_key), None)
        if not project_id:
            self._logger.error("Project '%s' not found.", project_key)
            return []

        request_url = f"{self.jira_server}/rest/tests/1.0/project/{project_id}/foldertree/{folder_type.replace('_', '').lower()}?startAt=0&maxResults=200"
        self._logger.debug("Getting folders in project '%s'", project_key)
        request = self._get(request_url)
        return build_folder_names(request.json()) if request else []

    def create_folder(self, project_key: str, folder_type: str, folder_name: str) -> Optional[int]:
        """
        Create a new folder if it does not exist.

        :param project_key: Project key of the folder ex. "TEST"
        :param folder_type: Type of the folder to be created ("TEST_CASE", "TEST_PLAN" or "TEST_RUN")
        :param folder_name: Name of the folder to be created
        :return: ID of the folder created
        """
        folder_name = f"/{folder_name}".replace("//", "/")
        if folder_name == "/" or folder_name in self.get_folders(project_key, folder_type):
            return None

        request_url = f"{self._adaptavist_api_url}/folder"
        request_data = {
            "projectKey": project_key,
            "name": folder_name,
            "type": folder_type,
        }
        self._logger.debug("Creating folder '%s' (%s) in project '%s'", folder_name, folder_type, project_key)
        request = self._post(request_url, request_data)
        return request.json()["id"] if request else None

    def get_test_case(self, test_case_key: str) -> Dict[str, Any]:
        """
        Get info about a test case.

        :param test_case_key: Test case key to look for
        :returns: Info about test case
        """
        request_url = f"{self._adaptavist_api_url}/testcase/{test_case_key}"
        self._logger.debug("Getting tets case '%s')", test_case_key)
        request = self._get(request_url)
        return request.json() if request else {}

    def get_test_cases(self, search_mask: str = "folder <= \"/\"") -> List[Dict[str, Any]]:
        """
        Get a list of test cases matching the search mask.
        Unfortunately, /testcase/search does not support empty query, so we use a basic filter here to get all test cases, if no search mask is given.

        :param search_mask: Search mask to match test cases
        :returns: List of test cases
        """
        test_cases: List[Dict[str, Any]] = []
        i = 0
        while True:
            request_url = f"{self._adaptavist_api_url}/testcase/search?query={quote_plus(search_mask)}&startAt={i}"
            self._logger.debug("Asking for test cases with search mask '%s' starting at %i", search_mask, i + 1)
            request = self._get(request_url)
            result = [] if not request else request.json()
            if not result:
                break
            test_cases = [*test_cases, *result]
            i += len(result)

        return test_cases

    def create_test_case(self, project_key: str, test_case_name: str, **kwargs: Any) -> Optional[int]:
        """
        Create a new test case.

        :param project_key: Project key of the test case ex. "TEST"
        :param test_case_name: Name of the test case to be created
        :key folder: Name of the folder where to create the new test case
        :key objective: Objective of the new test case, i.e. the overall description of its purpose
        :key precondition: Precondition(s) to be given in order to be able to execute this test case
        :key priority: Priority of the test case (e.g. "Low", "Normal", "High")
        :key estimated_time: Estimated execution time in seconds
        :key status: Status of the test case (e.g. "Draft" or "Approved")
        :key labels: List of labels to be added
        :key issue_links: List of issue keys to link the new test case to
        :key steps: List of steps to add. Each step as a dictionary (like {"description": <string>, "expectedResult": <string>}).
        :return: ID of the test plan created
        """
        folder: str = f"/{kwargs.pop('folder', '')}".replace("//", "/")  # Folders always need to start with /
        objective: str = kwargs.pop("objective", "")
        precondition: str = kwargs.pop("precondition", "")
        priority: str = kwargs.pop("priority", PRIORITY_NORMAL)
        estimated_time: int = kwargs.pop("estimated_time", 0) * 1000  # We actually need it in milliseconds
        status: str = kwargs.pop("status", STATUS_APPROVED)
        labels: List[str] = kwargs.pop("labels", [])
        issue_links: List[str] = kwargs.pop("issue_links", [])
        steps: List[Dict[str, Any]] = kwargs.pop("steps", [])
        raise_on_kwargs_not_empty(kwargs)

        self.create_folder(project_key=project_key, folder_type=TEST_CASE, folder_name=folder)

        request_url = f"{self._adaptavist_api_url}/testcase"
        request_data = {
            "projectKey": project_key,
            "name": test_case_name,
            "folder": None if folder == "/" else folder,  # The API uses null for the root folder
            "status": status,
            "objective": objective,
            "precondition": precondition,
            "priority": priority,
            "estimatedTime": estimated_time or None,
            "labels": labels,
            "issueLinks": issue_links,
            "testScript": {
                "type": STEP_TYPE_BY_STEP, "steps": steps
            },
        }
        self._logger.debug("Creating test case %s", project_key)
        request = self._post(request_url, request_data)
        return request.json()["key"] if request else None

    def edit_test_case(self, test_case_key: str, **kwargs: Any) -> bool:
        """
        Edit given test case.

        :param test_case_key: Test case key to be edited. ex. "JQA-T1234"
        :key folder: Folder to move the test case into - if not given, folder is not changed
        :key name: Name of the test case
        :key objective: Objective of the test case, i.e. the overall description of its purpose
        :key precondition: Precondition(s) to be given in order to be able to execute this test case
        :key priority: Priority of the test case (e.g. "Low", "Normal", "High")
        :key estimated_time: Estimated execution time in seconds
        :key status: Status of the test case (e.g. "Draft" or "Approved")
        :key labels: List of labels to be added (add a "-" as first list entry to create a new list)
        :key issue_links: List of issue keys to link the test case to (add a "-" as first list entry to create a new list)
        :key build_urls: List of build urls to be added (add a "-" as first list entry to create a new list)
        :key code_bases: List of code base urls to be added (add a "-" as first list entry to create a new list)
        :returns: True if succeeded, False if not
        """
        folder: Optional[str] = kwargs.pop("folder", None)
        name: str = kwargs.pop("name", "")
        objective: str = kwargs.pop("objective", "")
        precondition: str = kwargs.pop("precondition", "")
        priority: str = kwargs.pop("priority", "")
        estimated_time: int = kwargs.pop("estimated_time", 0) * 1000  # We actually need it in milliseconds
        status: str = kwargs.pop("status", "")
        labels: List[str] = kwargs.pop("labels", [])
        issue_links: List[str] = kwargs.pop("issue_links", [])
        build_urls: List[str] = kwargs.pop("build_urls", [])
        code_bases: List[str] = kwargs.pop("code_bases", [])
        raise_on_kwargs_not_empty(kwargs)

        response = self.get_test_case(test_case_key)
        if not response:
            return False

        request_url = f"{self._adaptavist_api_url}/testcase/{test_case_key}"
        request_data = {
            "name": name or response.get("name"),
            "objective": objective or response.get("objective"),
            "precondition": precondition or response.get("precondition"),
            "priority": priority or response.get("priority"),
            "estimatedTime": estimated_time or response.get("estimatedTime"),
            "status": status or response.get("status")
        }

        if folder is not None:
            folder = f"/{folder}".replace("//", "/")
            self.create_folder(project_key=response["projectKey"], folder_type=TEST_CASE, folder_name=folder)
            request_data["folder"] = folder if folder != "/" else None

        # append labels and issue links to the current list or create new ones
        update_field(response.get("labels", []), request_data, "labels", labels)
        update_field(response.get("issueLinks", []), request_data, "issueLinks", issue_links)

        # handle custom fields
        update_multiline_field(response.get("customFields", {}).get("ci_server_url", ""), request_data, "ci_server_url", build_urls)
        update_multiline_field(response.get("customFields", {}).get("code_base_url", ""), request_data, "code_base_url", code_bases)

        self._logger.debug("Updating data of test case '%s'", test_case_key)
        return bool(self._put(request_url, request_data))

    def delete_test_case(self, test_case_key: str) -> bool:
        """
        Delete given test case.

        :param test_case_key: Test case key to be deleted. ex. "JQA-T1234"
        :returns: True if succeeded, False if not
        """
        request_url = f"{self._adaptavist_api_url}/testcase/{test_case_key}"
        self._logger.debug("Deleting test case %s)", test_case_key)
        return bool(self._delete(request_url))

    def get_test_case_links(self, issue_key: str) -> List[Dict[str, str]]:
        """
        Get the list of test cases linked to an issue.

        :param issue_key: Issue key to look for
        :returns: List of linked test cases
        """
        request_url = f"{self._adaptavist_api_url}/issuelink/{issue_key}/testcases"
        self._logger.debug("Getting list of issues linked to %s", issue_key)
        request = self._get(request_url)
        return request.json() if request else []

    def link_test_cases(self, issue_key: str, test_case_keys: List[str]) -> bool:
        """
        Link a list of existing testcases to an issue.

        :param issue_key: Issue to link the test cases to
        :param test_case_keys: List of test case keys to be linked to the issue
        :returns: True if succeeded, False if not
        """
        for test_case_key in test_case_keys:
            response = self.get_test_case(test_case_key)
            if not response:
                self._logger.warning("Test case %s was not found", test_case_key)
                continue

            # append issue to the current list of issue links
            request_url = f"{self._adaptavist_api_url}/testcase/{test_case_key}"
            issue_links = response.get("issueLinks", [])
            if issue_key not in issue_links:
                issue_links.append(issue_key)

                request_data = {"issueLinks": issue_links}
                self._logger.debug("Adding links to test case %s", test_case_key)
                if not self._put(request_url, request_data):
                    return False

        return True

    def unlink_test_cases(self, issue_key: str, test_case_keys: List[str]) -> bool:
        """
        Unlink a list of existing testcases from an issue.

        :param issue_key: Issue to unlink the test cases from
        :param test_case_keys: List of test case keys to be unlinked from the issue
        :returns: True if succeeded, False if not
        """
        for test_case_key in test_case_keys:
            response = self.get_test_case(test_case_key)
            if not response:
                self._logger.warning("Test case %s was not found", test_case_key)
                continue

            # remove issue from the current list of issue links
            request_url = f"{self._adaptavist_api_url}/testcase/{test_case_key}"
            issue_links = response.get("issueLinks", [])
            if issue_key in issue_links:
                issue_links.remove(issue_key)

                request_data = {"issueLinks": issue_links}
                self._logger.debug("Removing links from test case %s", test_case_key)
                if not self._put(request_url, request_data):
                    return False

        return True

    def get_test_plan(self, test_plan_key: str) -> Dict[str, Any]:
        """
        Get info about a test plan.

        :param test_plan_key: Test plan key to look for
        :returns: Info about test plan
        """
        request_url = f"{self._adaptavist_api_url}/testplan/{test_plan_key}"
        self._logger.debug("Getting test plan %s", test_plan_key)
        request = self._get(request_url)
        return request.json() if request else {}

    def get_test_plans(self, search_mask: str = "folder <= \"/\"") -> List[Dict[str, Any]]:
        """
        Get a list of test plans matching the search mask.
        Unfortunately, /testplan/search does not support empty query, so we use a basic filter here to get all test plans, if no search mask is given.

        :param search_mask: Search mask to match test plans
        :returns: List of test plans
        """
        test_plans: List[Dict[str, Any]] = []
        i = 0
        while True:
            request_url = f"{self._adaptavist_api_url}/testplan/search?query={quote_plus(search_mask)}&startAt={i}"
            self._logger.debug("Asking for test plans with search mask '%s' starting at %i", search_mask, i + 1)
            request = self._get(request_url)
            result = request.json() if request else []
            if not result:
                break
            test_plans = [*test_plans, *result]
            i += len(result)
        return test_plans

    def create_test_plan(self, project_key: str, test_plan_name: str, **kwargs: Any) -> Optional[str]:
        """
        Create a new test plan.

        :param project_key: Project key of the test plan ex. "TEST"
        :param test_plan_name: Name of the test plan to be created
        :key folder: Name of the folder where to create the new test plan
        :key objective: Objective of the new test plan
        :key status: Status of the test case (e.g. "Draft" or "Approved")
        :key labels: List of labels to be added
        :key issue_links: List of issue keys to link the new test plan to
        :key test_runs: List of test run keys to be linked to the test plan ex. ["TEST-R2","TEST-R7"]
        :return: Key of the test plan created
        """
        folder: str = f"/{kwargs.pop('folder', '')}".replace("//", "/")  # Folders always need to start with /
        objective: str = kwargs.pop("objective", "")
        status: str = kwargs.pop("status", STATUS_APPROVED)
        labels: List[str] = kwargs.pop("labels", [])
        issue_links: List[str] = kwargs.pop("issue_links", [])
        test_runs: List[str] = kwargs.pop("test_runs", [])
        raise_on_kwargs_not_empty(kwargs)

        self.create_folder(project_key=project_key, folder_type=TEST_PLAN, folder_name=folder)

        request_url = f"{self._adaptavist_api_url}/testplan"
        request_data = {
            "projectKey": project_key,
            "name": test_plan_name,
            "folder": None if folder == "/" else folder,  # The API uses null for the root folder
            "status": status,
            "objective": objective,
            "labels": labels,
            "issueLinks": issue_links,
            "testRunKeys": test_runs,
        }

        self._logger.debug("Creating test plan %s in project %s", test_plan_name, project_key)
        request = self._post(request_url, request_data)
        return request.json()["key"] if request else None

    def edit_test_plan(self, test_plan_key: str, **kwargs: Any) -> bool:
        """
        Edit given test plan.

        :param test_plan_key: Test plan key to be edited. ex. "JQA-P1234"
        :key folder: Folder to move the test plan into
        :key name: Name of the test plan
        :key objective: Objective of the test plan
        :key status: Status of the test case (e.g. "Draft" or "Approved")
        :key labels: List of labels to be added (add a "-" as first list entry to create a new list)
        :key issue_links: List of issue keys to link the test plan to (add a "-" as first list entry to create a new list)
        :key test_runs: List of test run keys to be linked/added to the test plan ex. ["TEST-R2","TEST-R7"] (add a "-" as first list entry to create a new list)
        :returns: True if succeeded, False if not
        """
        folder: Optional[str] = kwargs.pop("folder", None)
        name: str = kwargs.pop("name", "")
        objective: str = kwargs.pop("objective", "")
        status: str = kwargs.pop("status", "")
        labels: List[str] = kwargs.pop("labels", [])
        issue_links: List[str] = kwargs.pop("issue_links", [])
        test_runs: List[str] = kwargs.pop("test_runs", [])
        raise_on_kwargs_not_empty(kwargs)

        response = self.get_test_plan(test_plan_key)
        if not response:
            return False

        request_url = f"{self._adaptavist_api_url}/testplan/{test_plan_key}"
        request_data = {
            "name": name or response.get("name"),
            "objective": objective or response.get("objective"),
            "status": status or response.get("status"),
        }

        if folder is not None:
            folder = f"/{folder}".replace("//", "/")
            self.create_folder(project_key=response["projectKey"], folder_type=TEST_CASE, folder_name=folder)
            request_data["folder"] = folder if folder != "/" else None

        # append labels, test runs and issue links to the current list or create new ones
        update_field(response.get("labels", []), request_data, "labels", labels)
        update_field([test_run["key"] for test_run in response.get("testRuns", [])], request_data, "testRuns", test_runs)
        update_field(response.get("issueLinks", []), request_data, "issueLinks", issue_links)

        self._logger.debug("Updating test plan %s", test_plan_key)
        return bool(self._put(request_url, request_data))

    def get_test_run(self, test_run_key: str) -> Dict[str, Any]:
        """
        Get info about a test run.

        :param test_run_key: Test run key to look for
        :returns: Info about the test run
        """
        request_url = f"{self._adaptavist_api_url}/testrun/{test_run_key}"
        self._logger.debug("Getting test run %s", test_run_key)
        request = self._get(request_url)
        return request.json() if request else {}

    def get_test_run_by_name(self, test_run_name: str) -> Dict[str, Any]:
        """
        Get info about a test run (last one found by name).

        .. note:: This method is using JIRA API as Adaptavist API does not support this properly (would be too slow to get this info).

        :param test_run_name: Test run name to look for
        :returns: Info about the test run
        """
        test_runs: List[Dict[str, Any]] = []
        i = 0
        search_mask = quote_plus(f"testRun.name = \"{test_run_name}\"")
        while True:
            request_url = f"{self.jira_server}/rest/tests/1.0/testrun/search?startAt={i}&maxResults=10000&query={search_mask}&fields=id,key,name"
            self._logger.debug("Asking for 10000 test runs starting at %i", i + 1)
            request = self._get(request_url)
            results = [] if not request else request.json()["results"]
            if not results:
                break
            test_runs = [*test_runs, *results]
            i += len(results)
        return {key: test_runs[-1][key] for key in ["key", "name"]} if test_runs else {}

    def get_test_runs(self, search_mask: str = "folder = \"/\"", **kwargs: Any) -> List[Dict[str, Any]]:
        """
        Get a list of test runs matching the search mask.
        Unfortunately, /testrun/search does not support empty query, so we use a basic filter here to get all test runs, if no search mask is given.

        :param search_mask: Search mask to match test runs
        :key fields: Comma-separated list of fields to be included (e.g. key, name, items)

        .. note:: If fields is not set, all fields will be returned. This can be slow as it will also also include test result items.

        :returns: List of test runs
        """
        fields: str = kwargs.pop("fields", "")
        raise_on_kwargs_not_empty(kwargs)

        test_runs: List[Dict[str, Any]] = []
        i = 0
        while True:
            request_url = f"{self._adaptavist_api_url}/testrun/search?query={quote_plus(search_mask)}&startAt={i}&maxResults=1000&fields={quote_plus(fields)}"
            self._logger.debug("Asking for 1000 test runs starting at %i using search mask %s", i + 1, search_mask)
            request = self._get(request_url)
            result = [] if not request else request.json()
            if not result:
                break
            test_runs = [*test_runs, *result]
            i += len(result)
        return test_runs

    def get_test_run_links(self, issue_key: str) -> List[Dict[str, str]]:
        """
        Get a list of test runs linked to an issue.

        :param issue_key: Issue key to look for
        :returns: List of linked test runs
        """
        test_runs = self.get_test_runs()
        self._logger.debug("Looking for test runs linked to %s", issue_key)
        return [test_run for test_run in test_runs if test_run["issueKey"] == issue_key]

    def create_test_run(self, project_key: str, test_run_name: str, **kwargs: Any) -> Optional[str]:
        """
        Create a new test run.

        :param project_key: Project key of the test run ex. "TEST"
        :param test_run_name: Name of the test run to be created
        :key folder: Name of the folder where to create the new test run
        :key issue_key: Issue key to link this test run to
        :key test_plan_key: Test plan key to link this test run to
        :key test_cases: List of test case keys to be linked to the test run ex. ["TEST-T1026","TEST-T1027"]
        :key environment: Environment to distinguish multiple executions (call get_environments() to get a list of available ones)
        :key version: Application version that should be used for test cycle execution
        :return: Key of the test run created
        """
        folder: str = f"/{kwargs.pop('folder', '')}".replace("//", "/")
        issue_key: str = kwargs.pop("issue_key", "")
        test_plan_key: str = kwargs.pop("test_plan_key", "")
        test_cases: List[str] = kwargs.pop("test_cases", [])
        environment: str = kwargs.pop("environment", "")
        version: str = kwargs.pop("version", "")
        raise_on_kwargs_not_empty(kwargs)

        self.create_folder(project_key=project_key, folder_type=TEST_RUN, folder_name=folder)

        test_cases_list_of_dicts = [{
            "testCaseKey": test_case_key,
            "environment": environment or None,
            "version": version or None,
        } for test_case_key in test_cases]

        request_url = f"{self._adaptavist_api_url}/testrun"
        request_data = {
            "projectKey": project_key,
            "testPlanKey": test_plan_key or None,
            "name": test_run_name,
            "version": version or None,
            "folder": None if folder == "/" else folder,  # The API uses null for the root folder
            "issueKey": issue_key or None,
            "items": test_cases_list_of_dicts,
        }
        self._logger.debug("Creating new test run in project %s with name '%s'", project_key, test_run_name)
        request = self._post(request_url, request_data)
        return request.json()["key"] if request else None

    def clone_test_run(self, test_run_key: str, test_run_name: str = "", **kwargs: Any) -> Optional[str]:
        """
        Clone a given test run.

        :param test_run_key: Test run key to be cloned
        :param test_run_name: Name of the test run clone (if empty, original name is used with appropriate suffix)
        :key folder: Name of the folder where to create the new test run
        :key test_plan_key: Test plan key to link this test run to
        :key environment: Environment to distinguish multiple executions (call get_environments() to get a list of available ones)
        :return: Key of the test run clone
        """
        folder: str = kwargs.pop("folder", "")
        test_plan_key: str = kwargs.pop("test_plan_key", "")
        project_key: str = kwargs.pop("project_key", "")
        environment: str = kwargs.pop("environment", "")
        raise_on_kwargs_not_empty(kwargs)

        test_run = self.get_test_run(test_run_key)
        if not test_run:
            return None

        test_run_items = test_run.get("items", [])

        key = self.create_test_run(
            project_key=project_key or test_run["projectKey"],
            test_run_name=test_run_name or f"{test_run['name']} (cloned from {test_run['key']})",
            folder=folder or test_run.get("folder"),
            issue_key=test_run.get("issueKey"),
            test_plan_key=test_plan_key,  # will be handled further below
            environment=environment or (test_run_items[0].get("environment", "") if test_run_items else ""),
            test_cases=[item["testCaseKey"] for item in test_run_items])

        # get test plans that contain the original test run and add cloned test run to them
        if key and not test_plan_key:
            for test_plan in self.get_test_plans():
                test_runs: List[Dict[str, Any]] = test_plan.get("testRuns", [])
                if test_run["key"] in [item["key"] for item in test_runs]:
                    self.edit_test_plan(test_plan_key=test_plan["key"], test_runs=[key])

        return key

    def get_test_execution_results(self, last_result_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all test results.

        .. note:: This method is using JIRA API and is much faster than getting test results for each test run via Adaptavist API.
                  By simple transposing the result list it is possible to get all the results based on test run keys.

        :param last_result_only: If true, returns only the last test result of each single test execution
                                 If false, returns all test results, i.e. even those ones that have been overwritten
        :returns: Test results
        """
        test_results: List[Dict[str, Any]] = []
        i = 0
        while True:
            request_url = f"{self.jira_server}/rest/tests/1.0/reports/testresults?startAt={i}&maxResults=10000"
            self._logger.debug("Asking for 10000 test results starting at %i", i + 1)
            request = self._get(request_url)
            results = [] if not request else request.json()["results"]
            if not results:
                break
            test_results = [*test_results, *results]
            i += len(results)

        results = [{
            "key": result["key"],
            "testCase": result.get("testCase", {}),
            "testRun": result.get("testRun", {}),
            "estimatedTime": result.get("estimatedTime"),
            "executedBy": result["user"].get("key"),
            "executionDate": result.get("executionDate"),
            "executionTime": result.get("executionTime"),
            "environment": result.get("environment", {}).get("name"),
            "assignedTo": result.get("assignedTo"),
            "automated": result.get("automated", False),
            "status": result["status"]["name"],
            "issueLinks": result.get("issues", []),
        } for result in test_results if result.get("lastTestResult", True) or not last_result_only]

        return results

    def get_test_results(self, test_run_key: str) -> List[Dict[str, Any]]:
        """
        Get all test results for a given test run.

        :param test_run_key: Test run key of the result to be updated. ex. "JQA-R1234"
        :returns: Test results
        """
        request_url = f"{self._adaptavist_api_url}/testrun/{test_run_key}/testresults"
        self._logger.debug("Getting all test results for run %s", test_run_key)
        request = self._get(request_url)
        if not request:
            return []
        results = request.json()
        for result in results:
            result["scriptResults"] = sorted(result["scriptResults"], key=lambda result: result["index"])
        return results

    def create_test_results(self, test_run_key: str, results: List[Dict[str, Any]], exclude_existing_test_cases: bool = True, **kwargs: Any) -> List[int]:
        """
        Create new test results for a given test run.

        :param test_run_key: Test run key of the result to be updated. ex. "JQA-R1234"
        :param results: Results to report
        :param exclude_existing_test_cases: If true, creates test results only for new test cases (can be used to add test cases to existing test runs)
                                            If false, creates new test results for existing test cases as well
        :key environment: Environment to distinguish multiple executions (call get_environments() to get a list of available ones)
        :key assignee: Assignee of the test case. Use "" for unassigned, None to determine automatically
        :key executor: Executer of the test case. Use "" for unassigned, None to determine automatically
        :return: List of ids of all the test results that were created
        """
        environment: str = kwargs.pop("environment", "")
        assignee: Optional[str] = kwargs.pop("assignee", None)
        executor: Optional[str] = kwargs.pop("executor", None)
        raise_on_kwargs_not_empty(kwargs)

        test_run = self.get_test_run(test_run_key)
        if not test_run:
            return []

        assignee = get_executor() if assignee is None else assignee
        executor = get_executor() if executor is None else executor
        request_data = []
        for result in results:
            if exclude_existing_test_cases and result["testCaseKey"] in [item["testCaseKey"] for item in test_run["items"]]:
                continue
            result["assignedTo"] = assignee or None  # The API uses null for unassigned
            result["executedBy"] = executor or None  # The API uses null for unassigned
            result["environment"] = environment or None
            request_data.append(result)

        if not request_data:
            return []

        request_url = f"{self._adaptavist_api_url}/testrun/{test_run_key}/testresults"
        self._logger.debug("Creating test results for run %s", test_run_key)
        request = self._post(request_url, request_data)

        return [result["id"] for result in request.json()] if request else []

    def get_test_result(self, test_run_key: str, test_case_key: str) -> Dict[str, Any]:
        """
        Get the test result for a given test run and test case.

        :param test_run_key: Test run key of the result to be updated. ex. "JQA-R1234"
        :param test_case_key: Test case key of the result to be updated. ex. "JQA-T1234"
        :returns: Test result
        """
        response = self.get_test_results(test_run_key)
        for item in response:
            if item["testCaseKey"] == test_case_key:
                return item
        return {}

    def create_test_result(self, test_run_key: str, test_case_key: str, status: str = STATUS_NOT_EXECUTED, **kwargs: Any) -> Optional[int]:
        """
        Create a new test result for a given test run and test case with the given status.

        :param test_run_key: Test run key of the result to be created. ex. "JQA-R1234"
        :param test_case_key: Test case key of the result to be created. ex. "JQA-T1234"
        :param status: Status of the result to be created. ex. "Fail"
        :key comment: Comment to add
        :key execute_time: Execution time in seconds
        :key environment: Environment to distinguish multiple executions (call get_environments() to get a list of available ones)
        :key assignee: Assignee of the test case. Use "" for unassigned, None to determine automatically
        :key executor: Executer of the test case. Use "" for unassigned, None to determine automatically
        :key issue_links: List of issue keys to link the test result to
        :return: ID of the test result that was created
        """
        comment: str = kwargs.pop("comment", "")
        execute_time: Optional[int] = kwargs.pop("execute_time", None)
        environment: str = kwargs.pop("environment", "")
        assignee: Optional[str] = kwargs.pop("assignee", None)
        executor: Optional[str] = kwargs.pop("executor", None)
        issue_links: List[str] = kwargs.pop("issue_links", [])
        raise_on_kwargs_not_empty(kwargs)

        request_url = f"{self._adaptavist_api_url}/testrun/{test_run_key}/testcase/{test_case_key}/testresult"

        assignee = get_executor() if assignee is None else assignee
        executor = get_executor() if executor is None else executor
        request_data: Dict[str, Any] = {
            "comment": comment,
            "environment": environment or None,
            "assignedTo": assignee or None,  # The API uses null for unassigned
            "executedBy": executor or None,  # The API uses null for unassigned
            "status": status,
        }
        if execute_time is not None:
            request_data["executionTime"] = execute_time * 1000
        if issue_links:
            request_data["issueLinks"] = issue_links

        self._logger.debug("Creating test result for %s in %s", test_case_key, test_run_key)
        request = self._post(request_url, request_data)
        return request.json()["id"] if request else None

    def edit_test_result_status(self, test_run_key: str, test_case_key: str, status: str, **kwargs: Any) -> bool:
        """
        Edit the last existing test result for a given test run and test case with the given status.

        :param test_run_key: Test run key of the result to be created. ex. "JQA-R1234"
        :param test_case_key: Test case key of the result to be created. ex. "JQA-T1234"
        :param status: Status of the result to be created. ex. "Fail"
        :key comment: Comment to the new status
        :key execute_time: Execution time in seconds
        :key environment: Environment to distinguish multiple executions (call get_environments() to get a list of available ones)
        :key assignee: Assignee of the test case. Use "" for unassigned
        :key executor: Executer of the test case. Use "" for unassigned
        :key issue_links: List of issue keys to link the test result to
        :return: True if succeeded, False if not
        """
        comment: Optional[str] = kwargs.pop("comment", None)
        execute_time: Optional[int] = kwargs.pop("execute_time", None)
        environment: Optional[str] = kwargs.pop("environment", None)
        assignee: Optional[str] = kwargs.pop("assignee", None)
        executor: Optional[str] = kwargs.pop("executor", None)
        issue_links: Optional[List[str]] = kwargs.pop("issue_links", None)
        raise_on_kwargs_not_empty(kwargs)

        request_url = f"{self._adaptavist_api_url}/testrun/{test_run_key}/testcase/{test_case_key}/testresult"
        request_data: Dict[str, Any] = {
            "status": status,
        }
        if environment is not None:
            request_data["environment"] = environment
        if assignee is not None:
            request_data["assignedTo"] = assignee or None
        if executor is not None:
            request_data["executedBy"] = executor or None
        if comment is not None:
            request_data["comment"] = comment
        if execute_time is not None:
            request_data["executionTime"] = execute_time * 1000
        if issue_links is not None:
            request_data["issueLinks"] = issue_links

        self._logger.debug("Updating test result for %s in %s", test_case_key, test_run_key)
        return bool(self._put(request_url, request_data))

    def get_test_result_attachment(self, test_run_key: str, test_case_key: str) -> List[Dict[str, Any]]:
        """
        Add attachment to a test result.

        :param test_run_key: Test run key. ex. "JQA-R1234"
        :param test_case_key: Test case key. ex. "JQA-T1234"
        :returns: Test result attachments
        """
        test_result_id = self.get_test_result(test_run_key, test_case_key)['id']
        request_url = f"{self._adaptavist_api_url}/testresult/{test_result_id}/attachments"
        request = self._get(request_url)
        return request.json() if request else []

    def add_test_result_attachment(self, test_run_key: str, test_case_key: str, attachment: Union[str, BinaryIO], filename: str = "") -> bool:
        """
        Add attachment to a test result.

        :param test_run_key: Test run key. ex. "JQA-R1234"
        :param test_case_key: Test case key. ex. "JQA-T1234"
        :param attachment: The attachment as filepath name or file-like object
        :param filename: The optional filename
        :returns: True if succeeded, False if not
        """
        test_result_id = self.get_test_result(test_run_key, test_case_key)['id']
        request_url = f"{self._adaptavist_api_url}/testresult/{test_result_id}/attachments"
        return self._upload_file_by_name(request_url, attachment, filename) \
            if isinstance(attachment, str) \
            else self._upload_file(request_url, attachment, filename)

    def edit_test_script_status(self, test_run_key: str, test_case_key: str, step: int, status: str, **kwargs: Any) -> bool:
        """
        Edit test script result for a given test run and test case with the given status.

        :param test_run_key: Test run key of the result to be updated. ex. "JQA-R1234"
        :param test_case_key: Test case key of the result to be updated. ex. "JQA-T1234"
        :param step: Index (starting from 1) of step to be updated
        :param status: Status of the result to be updated. ex. "Fail"
        :key comment: Comment to the new status
        :key environment: Environment to distinguish multiple executions (call get_environments() to get a list of available ones)
        :key assignee: Assignee of the test case. Use "" for unassigned, None to determine automatically
        :key executor: Executer of the test case. Use "" for unassigned, None to determine automatically
        :return: True if succeeded, False if not
        """
        comment: Optional[str] = kwargs.pop("comment", None)
        environment: Optional[str] = kwargs.pop("environment", None)
        assignee: Optional[str] = kwargs.pop("assignee", None)
        executor: Optional[str] = kwargs.pop("executor", None)
        raise_on_kwargs_not_empty(kwargs)

        test_result = self.get_test_result(test_run_key, test_case_key)
        script_results = test_result.get("scriptResults", [])

        for script_result in script_results:
            # keep relevant fields only (to make PUT pass)
            for key in list(script_result):
                if key not in ["index", "status", "comment"]:
                    script_result.pop(key)

            # update given step
            if script_result["index"] == step - 1:
                script_result["status"] = status
                script_result["comment"] = comment

        request_url = f"{self._adaptavist_api_url}/testrun/{test_run_key}/testcase/{test_case_key}/testresult"
        request_data = {
            "status": test_result["status"],  # mandatory, to keep test result status unchanged
            "scriptResults": script_results,
        }
        if environment is not None:
            request_data["environment"] = environment
        if assignee is not None:
            request_data["assignedTo"] = assignee or None
        if executor is not None:
            request_data["executedBy"] = executor or None

        self._logger.debug("Updating test script for %s in %s", test_case_key, test_run_key)
        return bool(self._put(request_url, request_data))

    def get_test_script_attachment(self, test_run_key: str, test_case_key: str, step: int) -> List[Dict[str, Any]]:
        """
        Get attachments of a test script result.

        :param test_run_key: Test run key. ex. "JQA-R1234"
        :param test_case_key: Test case key. ex. "JQA-T1234"
        :param step: Index (starting from 1) of step to get the attachments from.
        :returns: Test script result attachments
        """
        test_result_id = self.get_test_result(test_run_key, test_case_key)['id']
        request_url = f"{self._adaptavist_api_url}/testresult/{test_result_id}/step/{step - 1}/attachments"
        request = self._get(request_url)
        return request.json() if request else []

    def add_test_script_attachment(self, test_run_key: str, test_case_key: str, step: int, attachment: Union[str, BinaryIO], filename: str = "") -> bool:
        """
        Add attachment to a test script result.

        :param test_run_key: Test run key. ex. "JQA-R1234"
        :param test_case_key: Test case key. ex. "JQA-T1234"
        :param step: Index (starting from 1) of step to be updated.
        :param attachment: The attachment as filepath name or file-like object.
        :param filename: The optional filename.
        :returns: True if succeeded, False if not
        """
        test_result_id = self.get_test_result(test_run_key, test_case_key)['id']
        request_url = f"{self._adaptavist_api_url}/testresult/{test_result_id}/step/{step - 1}/attachments"
        return self._upload_file_by_name(request_url, attachment, filename) \
            if isinstance(attachment, str) \
            else self._upload_file(request_url, attachment, filename)

    def _delete(self, request_url: str) -> Optional[requests.Response]:
        """DELETE data from Jira/Adaptavist."""
        try:
            request = requests.delete(request_url, auth=self._authentication, headers=self._headers)
            request.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.RequestException) as ex:
            self._logger.error("request failed. %s", ex)
            return None
        return request

    def _get(self, request_url: str) -> Optional[requests.Response]:
        """GET data from Jira/Adaptavist."""
        try:
            request = requests.get(request_url, auth=self._authentication, headers=self._headers)
            request.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.RequestException) as ex:
            self._logger.error("request failed. %s", ex)
            return None
        return request

    def _post(self, request_url: str, data: Any) -> Optional[requests.Response]:
        """POST data to Jira/Adaptavist."""
        try:
            request = requests.post(request_url, auth=self._authentication, headers=self._headers, data=json.dumps(data))
            request.raise_for_status()
        except requests.exceptions.HTTPError as ex:
            self._logger.error("request failed. %s %s", ex, request.text)
            return None
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self._logger.error("request failed. %s", ex)
            return None
        return request

    def _put(self, request_url: str, data: Any) -> Optional[requests.Response]:
        """PUT data to Jira/Adaptavist."""
        try:
            request = requests.put(request_url, auth=self._authentication, headers=self._headers, data=json.dumps(data))
            request.raise_for_status()
        except requests.exceptions.HTTPError as ex:
            self._logger.error("request failed. %s %s", ex, request.text)
            return None
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self._logger.error("request failed. %s", ex)
            return None
        return request

    def _upload_file(self, request_url: str, attachment: BinaryIO, filename: str) -> bool:
        """Upload file to Adaptavist."""
        stream = requests_toolbelt.MultipartEncoder(fields={"file": (filename, attachment, "application/octet-stream")})
        headers = {**self._headers}
        headers["Content-type"] = stream.content_type
        headers["X-Atlassian-Token"] = "nocheck"
        filename = filename or attachment.name

        try:
            request = requests.post(request_url, auth=self._authentication, headers=headers, data=stream)
            request.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.RequestException) as ex:
            self._logger.error("request failed. %s", ex)
            return False
        return True

    def _upload_file_by_name(self, request_url: str, attachment: str, filename: str) -> bool:
        """Upload file by filename to Adaptavist."""
        if not filename:
            raise SyntaxError("No filename given.")
        try:
            fp = open(attachment, "rb")
        except OSError as ex:
            self._logger.error("attachment failed. %s", ex)
            return False
        success = self._upload_file(request_url, fp, filename)
        fp.close()
        return success
