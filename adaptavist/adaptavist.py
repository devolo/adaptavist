#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module provides functionality for Adaptavist Test Management with Jira server interaction."""

import json
import logging
import urllib.parse
from typing import Any, BinaryIO, Dict, List, Optional, Union

import requests
import requests_toolbelt

from ._helper import build_folder_names, get_executor, update_list, update_multiline_field


class Adaptavist():
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
        self._logger = logging.getLogger(self.__class__.__name__)

    def get_users(self) -> List[str]:
        """
        Get a list of users known to Adaptavist/Jira.

        :returns: List of user keys
        """
        users: List = []
        i = 0
        while True:
            request_url = f"{self.jira_server}/rest/api/2/user/search?username=.&startAt={i}&maxResults=200"
            self._logger.debug("Asking for 200 users starting at %i", i + 1)
            request = self._get(request_url)
            result = [] if not request else request.json()
            if not result:
                break
            users = [*users, *result]
            i += len(result)
        return [user["key"] for user in users]

    def get_projects(self) -> List[Dict[str, str]]:
        """
        Get a list of projects known to Adatavist/Jira.

        :returns: List of projects
        """

        request_url = f"{self.jira_server}/rest/tests/1.0/project"
        self._logger.debug("Asking for product list.")
        request = self._get(request_url)
        response = [] if not request else request.json()
        return [{"id": project["id"], "key": project["key"], "name": project["name"]} for project in response]

    def get_environments(self, project_key: str = "") -> List[Dict[str, str]]:
        """
        Get a list of environments matching the search mask.

        :param project_key: Project key to search for environments
        :returns: List of environments
        """
        request_url = f"{self._adaptavist_api_url}/environments?projectKey={urllib.parse.quote_plus(project_key)}"
        self._logger.debug("Asking enviroments in project '%s'.", project_key)
        request = self._get(request_url)
        return [] if not request else request.json()

    def create_environment(self, project_key: str, environment_name: str, **kwargs) -> Optional[int]:
        """
        Create a new environment.

        :param project_key: Project key of the environment ex. "TEST"
        :param environment_name: Name of the environment to be created
        :key description: Description of the environment
        :return: id of the environment created
        """
        description: str = kwargs.pop("description", "")
        if kwargs:
            raise SyntaxWarning("Unknown arguments: %r", kwargs)

        request_url = f"{self._adaptavist_api_url}/environments"
        self._logger.debug("Creating environment '%s' in project '%s'", environment_name, project_key)
        request_data = {"projectKey": project_key,
                        "name": environment_name,
                        "description": description}

        request = self._post(request_url, request_data)
        if request:
            response = request.json()
            return response["id"]
        return None

    def get_folders(self, project_key: str, folder_type: str) -> List[str]:
        """
        Get a list of folders.

        :param project_key: Project key to search for folders
        :param folder_type: Type of the folder to be created ("TEST_CASE", "TEST_PLAN" or "TEST_RUN")
        :returns: List of folders
        """
        # TODO: Use constants for folder_type
        project_id = next((project["id"] for project in self.get_projects() if project["key"] == project_key), None)

        if not project_id:
            self._logger.error(f"Project {project_key} not found.")
            return []

        request_url = f"{self.jira_server}/rest/tests/1.0/project/{urllib.parse.quote_plus(project_id)}/foldertree/{folder_type.replace('_', '')}?startAt=0&maxResults=200"
        self._logger.debug("Getting folders in project '%s'", project_key)
        request = self._get(request_url)
        response = [] if not request else request.json()

        return build_folder_names(response)

    def create_folder(self, project_key: str, folder_type: str, folder_name: str) -> Optional[int]:
        """
        Create a new environment.

        :param project_key: Project key of the environment ex. "TEST"
        :param folder_type: Type of the folder to be created ("TEST_CASE", "TEST_PLAN" or "TEST_RUN")
        :param folder_name: Name of the folder to be created
        :return: ID of the folder created
        """
        # TODO: Use constants for folder_type
        request_url = f"{self._adaptavist_api_url}/folder"
        request_data = {"projectKey": project_key,
                        "name": folder_name,
                        "type": folder_type}
        self._logger.debug("Creating folder '%s' (%s) in project '%s'", folder_name, folder_type, project_key)
        request = self._post(request_url, request_data)
        if not request:
            return None
        response = request.json()
        return response["id"]

    def get_test_case(self, test_case_key: str) -> Dict[str, str]:
        """
        Get info about a test case.

        :param test_case_key: Test case key to look for
        :returns: Info about test case
        """
        request_url = f"{self._adaptavist_api_url}/testcase/{test_case_key}"
        self._logger.debug("Getting tets case '%s')", test_case_key)
        request = self._get(request_url)
        return {} if not request else request.json()

    def get_test_cases(self, search_mask: str = "") -> List[Dict[str, str]]:
        """
        Get a list of test cases matching the search mask.

        :param search_mask: search mask to match test cases
        :returns: List of test cases
        """
        # unfortunately, /testcase/search does not support empty query, so we use a basic filter here to get all test cases
        search_mask = search_mask or "folder <= \"/\""

        test_cases: List = []
        i = 0
        while True:
            request_url = f"{self._adaptavist_api_url}/testcase/search?query={urllib.parse.quote_plus(search_mask)}&startAt={i}"
            self._logger.debug("Asking for test cases with search mask '%s' starting at %i", search_mask, i + 1)
            request = self._get(request_url)
            if not request:
                break
            result = request.json()
            test_cases = [*test_cases, *result]
            i += len(result)

        return test_cases

    def create_test_case(self, project_key: str, test_case_name: str, **kwargs) -> Optional[int]:
        """
        Create a new test case.

        :param project_key: Project key of the test case ex. "TEST"
        :param test_case_name: Name of the test case to be created
        :key folder: Name of the folder where to create the new test case
        :key objective: Objective of the new test case, i.e. the overall description of its purpose
        :key precondition: Precondition(s) to be given in order to be able to execute this test case
        :key priority: Priority of the test case (e.g. "Low", "Normal", "High")
        :key estimated_time: Estimated execution time in seconds
        :key labels: List of labels to be added
        :key issue_links: List of issue keys to link the new test case to
        :key steps: List of steps to add. Each step as a dictionary (like {"description": <string>, "expectedResult": <string>}).
        :return: ID of the test plan created
        """
        folder: str = kwargs.pop("folder", "")
        objective: str = kwargs.pop("objective", "")
        precondition: str = kwargs.pop("precondition", "")
        priority: str = kwargs.pop("priority", "")
        estimated_time: Optional[int] = kwargs.pop("estimated_time")
        labels: List[str] = kwargs.pop("labels", [])
        issue_links: List[str] = kwargs.pop("issue_links", [])
        steps: List[Dict[str, Any]] = kwargs.pop("steps", [])
        if kwargs:
            raise SyntaxWarning("Unknown arguments: %r", kwargs)

        folder = ("/" + folder).replace("//", "/") if folder else ""
        # TODO: Use constants for folder_type
        if folder and folder not in self.get_folders(project_key=project_key, folder_type="TEST_CASE"):
            self.create_folder(project_key=project_key, folder_type="TEST_CASE", folder_name=folder)

        request_url = f"{self._adaptavist_api_url}/testcase"
        # TODO: Use constants for step_type
        request_data = {"projectKey": project_key,
                        "name": test_case_name,
                        "folder": folder,
                        "status": "Approved",
                        "objective": objective,
                        "precondition": precondition,
                        "priority": priority,
                        "estimatedTime": estimated_time * 1000 if estimated_time is not None else None,
                        "labels": labels,
                        "issueLinks": issue_links,
                        "testScript": {"type": "STEP_BY_STEP", "steps": json.dumps(steps)}
                        }
        self._logger.debug("Creating test case %s", project_key)
        request = self._post(request_url, request_data)
        if not request:
            return None
        response = request.json()
        return response["id"]

    def edit_test_case(self, test_case_key: str, **kwargs) -> bool:
        """
        Edit given test case.

        :param test_case_key: Test case key to be edited. ex. "JQA-T1234"
        :key folder: Folder to move the test case into - if not given, folder is not changed - if set to None, folder will be (re-)moved to root
        :key name: Name of the test case
        :key objective: Objective of the test case, i.e. the overall description of its purpose
        :key precondition: Precondition(s) to be given in order to be able to execute this test case
        :key priority: Priority of the test case (e.g. "Low", "Normal", "High")
        :key estimated_time: estimated execution time in seconds.
        :key labels: List of labels to be added (add a "-" as first list entry to remove labels or to create a new list)
        :key issue_links: List of issue keys to link the test case to (add a "-" as first list entry to remove links or to create a new list)
        :key build_urls: List of build urls to be added (add a "-" as first list entry to remove urls or to create a new list)
        :key code_bases: List of code base urls to be added (add a "-" as first list entry to remove urls or to create a new list)
        :returns: True if succeeded, False if not
        """
        keep_original_value = r"\{keep_original_value\}"
        folder = kwargs.pop("folder", keep_original_value)  # differ between folder not passed and folder set to None (to move to root)
        name: str = kwargs.pop("name", "")
        objective: str = kwargs.pop("objective", "")
        precondition: str = kwargs.pop("precondition", "")
        priority: str = kwargs.pop("priority", "")
        estimated_time: Optional[int] = kwargs.pop("estimated_time")
        labels: List[str] = kwargs.pop("labels", [])
        issue_links: List[str] = kwargs.pop("issue_links", [])
        build_urls: List[str] = kwargs.pop("build_urls", [])
        code_bases: List[str] = kwargs.pop("code_bases", [])
        if kwargs:
            raise SyntaxWarning("Unknown arguments: %r", kwargs)

        request_url = f"{self._adaptavist_api_url}/testcase/{test_case_key}"
        self._logger.debug("Getting current data of test case '%s'", test_case_key)
        request = self._get(request_url)
        if not request:
            return False

        response = request.json()

        request_data = {"name": name or response.get("name"),
                        "objective": objective or response.get("objective"),
                        "precondition": precondition or response.get("precondition"),
                        "priority": priority or response.get("priority"),
                        "estimatedTime": estimated_time * 1000 if estimated_time is not None else response.get("estimatedTime")}

        self._logger.debug("edit_test_case(\"%s\")", test_case_key)
        folder = response.get("folder") if folder == keep_original_value else (("/" + folder).replace("//", "/") if folder else None)
        if folder != response.get("folder"):
            # TODO: Use constants for folder_type
            if folder and folder not in self.get_folders(project_key=response["projectKey"], folder_type="TEST_CASE"):
                self.create_folder(project_key=response["projectKey"], folder_type="TEST_CASE", folder_name=folder)
            request_data["folder"] = folder

        # append labels to the current list of labels or create new one
        current_values = response.get("labels", [])
        labels = update_list(current_values, labels)
        if labels != current_values:
            request_data["labels"] = labels

        # append issue links to the current list of issue links or create new ones
        current_values = response.get("issueLinks", [])
        issue_links = update_list(current_values, issue_links)
        if issue_links != current_values:
            request_data["issueLinks"] = issue_links

        # handle custom fields
        current_values = response.get("customFields", {}).get("ci_server_url", "")
        build_urls = update_multiline_field(current_values, build_urls)
        if build_urls != current_values:
            request_data.setdefault("customFields", {})["ci_server_url"] = build_urls

        current_values = response.get("customFields", {}).get("code_base_url", "")
        code_bases = update_multiline_field(current_values, code_bases)
        if code_bases != current_values:
            request_data.setdefault("customFields", {})["code_base_url"] = code_bases

        self._logger.debug("Updating data of test case '%s'", test_case_key)
        return bool(self._put(request_url, request_data))

    def delete_test_case(self, test_case_key: str) -> bool:
        """
        Delete given test case.

        :param test_case_key: test case key to be deleted. ex. "JQA-T1234"
        :returns: True if succeeded, False if not
        """
        request_url = f"{self._adaptavist_api_url}/testcase/{test_case_key}"
        self._logger.debug("Deleting test case %s)", test_case_key)
        return bool(self._delete(request_url))

    def get_test_case_links(self, issue_key: str) -> List[Dict[str, str]]:
        """
        Get the list of test cases linked to an issue.

        :param issue_key: issue key to look for
        :returns: List of linked test cases
        """
        request_url = f"{self._adaptavist_api_url}/issuelink/{issue_key}/testcases"
        self._logger.debug("Getting list of issues linked to %s", issue_key)
        request = self._get(request_url)
        return [] if not request else request.json()

    def link_test_cases(self, issue_key: str, test_case_keys: List[str]) -> bool:
        """
        Link a list of existing testcases to an issue.

        :param issue_key: issue to link the test cases to
        :param test_case_keys: list of test case keys to be linked to the issue
        :returns: True if succeeded, False if not
        """
        for test_case_key in test_case_keys:
            request_url = f"{self._adaptavist_api_url}/testcase/{test_case_key}"
            try:
                self._logger.debug("Getting test case %s", test_case_key)
                request = requests.get(request_url,
                                       auth=self._authentication,
                                       headers=self._headers)
                if request.status_code == 404:
                    self._logger.warning("Test case %s was not found", test_case_key)
                    continue
                request.raise_for_status()
            except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.RequestException) as ex:
                self._logger.error("request failed. %s", ex)
                return False

            response = request.json()

            # append issue to the current list of issue links
            issue_links = response.get("issueLinks", [])
            if issue_key not in issue_links:
                issue_links.append(issue_key)

                # according to doc only fields given in the request body are updated.
                request_data = {"issueLinks": issue_links}
                self._logger.debug("Updating test case %s", test_case_key)
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
            request_url = f"{self._adaptavist_api_url}/testcase/{test_case_key}"
            self._logger.debug("Getting test case %s", test_case_key)
            try:
                request = requests.get(request_url,
                                       auth=self._authentication,
                                       headers=self._headers)
                if request.status_code == 404:
                    self._logger.warning("Test case %s was not found", test_case_key)
                    continue
                request.raise_for_status()
            except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.RequestException) as ex:
                self._logger.debug("request failed. %s", ex)
                return False

            response = request.json()

            # remove issue from the current list of issue links
            issue_links = response.get("issueLinks", [])
            if issue_key in issue_links:
                issue_links.remove(issue_key)

                # according to doc only fields given in the request body are updated.
                request_data = {"issueLinks": issue_links}
                self._logger.debug("Updating test case %s", test_case_key)
                if not self._put(request_url, request_data):
                    return False

        return True

    def get_test_plan(self, test_plan_key: str) -> Dict[str, str]:
        """
        Get info about a test plan.

        :param test_plan_key: Test plan key to look for
        :returns: Info about test plan
        """
        request_url = f"{self._adaptavist_api_url}/testplan/{test_plan_key}"
        self._logger.debug("Getting test plan %s", test_plan_key)
        request = self._get(request_url)
        return {} if not request else request.json()

    def get_test_plans(self, search_mask: str = "") -> List[Dict[str, Any]]:
        """
        Get a list of test plans matching the search mask.

        :param search_mask: Search mask to match test plans
        :returns: List of test plans
        """
        # unfortunately, /testplan/search does not support empty query, so we use a basic filter here to get all test plans
        search_mask = search_mask or "folder <= \"/\""

        test_plans: List = []
        i = 0
        while True:
            request_url = f"{self._adaptavist_api_url}/testplan/search?query={urllib.parse.quote_plus(search_mask)}&startAt={i}"
            self._logger.debug("Asking for test plans with search mask '%s' starting at %i", search_mask, i + 1)
            request = self._get(request_url)
            result = [] if not request else request.json()
            if not result:
                break
            test_plans = [*test_plans, *result]
            i += len(result)
        return test_plans

    def create_test_plan(self, project_key: str, test_plan_name: str, **kwargs) -> Optional[str]:
        """
        Create a new test plan.

        :param project_key: Project key of the test plan ex. "TEST"
        :param test_plan_name: Name of the test plan to be created
        :key folder: Name of the folder where to create the new test plan
        :key objective: Objective of the new test plan
        :key labels: List of labels to be added
        :key issue_links: List of issue keys to link the new test plan to
        :key test_runs: List of test run keys to be linked to the test plan ex. ["TEST-R2","TEST-R7"]
        :return: Key of the test plan created
        """
        folder: str = kwargs.pop("folder", "")
        objective: str = kwargs.pop("objective", "")
        labels: List[str] = kwargs.pop("labels", [])
        issue_links: List[str] = kwargs.pop("issue_links", [])
        test_runs: List[str] = kwargs.pop("test_runs", [])
        # TODO: Introduce status
        if kwargs:
            raise SyntaxWarning("Unknown arguments: %r", kwargs)

        folder = ("/" + folder).replace("//", "/") if folder else ""
        # TODO: Use constants for folder_type
        if folder and folder not in self.get_folders(project_key=project_key, folder_type="TEST_PLAN"):
            self.create_folder(project_key=project_key, folder_type="TEST_PLAN", folder_name=folder)

        request_url = f"{self._adaptavist_api_url}/testplan"
        request_data = {"projectKey": project_key,
                        "name": test_plan_name,
                        "folder": folder,
                        "status": "Approved",
                        "objective": objective,
                        "labels": labels,
                        "issueLinks": issue_links,
                        "testRunKeys": test_runs,
                        }

        self._logger.debug("Creating test plan %s in project %s", test_plan_name, project_key)
        request = self._post(request_url, request_data)
        if request:
            response = request.json()
            return response["key"]
        return None

    def edit_test_plan(self, test_plan_key: str, **kwargs) -> bool:
        """
        Edit given test plan.

        :param test_plan_key: Test plan key to be edited. ex. "JQA-P1234"
        :key folder: Folder to move the test plan into
        :key name: Name of the test plan
        :key objective: Objective of the test plan
        :key labels: List of labels to be added (add a "-" as first list entry to remove labels or to create a new list)
        :key issue_links: List of issue keys to link the test plan to (add a "-" as first list entry to remove links or to create a new list)
        :key test_runs: List of test run keys to be linked/added to the test plan ex. ["TEST-R2","TEST-R7"] (add a "-" as first list entry to remove links or to create a new list)
        :returns: True if succeeded, False if not
        """
        keep_original_value = r"\{keep_original_value\}"
        folder: str = kwargs.pop("folder", keep_original_value)  # differ between folder not passed and folder set to None (to move to root)
        name: str = kwargs.pop("name", "")
        objective: str = kwargs.pop("objective", "")
        labels: List[str] = kwargs.pop("labels", [])
        issue_links: List[str] = kwargs.pop("issue_links", [])
        test_runs: List[str] = kwargs.pop("test_runs", [])
        # TODO: Introduce status
        if kwargs:
            raise SyntaxWarning("Unknown arguments: %r", kwargs)

        request_url = f"{self._adaptavist_api_url}/testplan/{test_plan_key}"
        self._logger.debug("Getting test plan %s", test_plan_key)
        request = self._get(request_url)
        if not request:
            return False

        response = request.json()

        request_data = {"name": name or response.get("name"),
                        "objective": objective or response.get("objective")}

        folder = response["folder"] if folder == keep_original_value else (("/" + folder).replace("//", "/") if folder else None)
        if folder != response["folder"]:
            # TODO: Use constants for folder_type
            if folder and folder not in self.get_folders(project_key=response.get("projectKey"), folder_type="TEST_PLAN"):
                self.create_folder(project_key=response.get("projectKey"), folder_type="TEST_PLAN", folder_name=folder)
            request_data.update({"folder": folder})

        # append labels to the current list of labels or create new one
        current_values = response.get("labels", [])
        labels = update_list(current_values, labels)
        if labels != current_values:
            request_data.update({"labels": labels})

        # append test runs to the current list of test runs or create new ones
        current_values = [test_run["key"] for test_run in response.get("testRuns", [])]
        test_runs = update_list(current_values, test_runs)
        if test_runs != current_values:
            request_data.update({"testRuns": test_runs})

        # append issue links to the current list of issue links or create new ones
        current_values = response.get("issueLinks", [])
        issue_links = update_list(current_values, issue_links)
        if issue_links != current_values:
            request_data.update({"issueLinks": issue_links})

        self._logger.debug("Updating test plan %s", test_plan_key)
        # according to doc only fields given in the request body are updated.
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
        return {} if not request else request.json()

    def get_test_run_by_name(self, test_run_name: str) -> Dict[str, str]:
        """
        Get info about a test run (last one found by name).

        .. note:: This method is using JIRA API as Adaptavist API does not support this properly (would be too slow to get this info).

        :param test_run_name: Test run name to look for
        :returns: Info about the test run
        """
        test_runs: List = []
        i = 0
        while True:
            search_mask = urllib.parse.quote_plus(f"testRun.name = \"{test_run_name}\"")
            request_url = f"{self.jira_server}/rest/tests/1.0/testrun/search?startAt={i}&maxResults=10000&query={search_mask}&fields=id,key,name"
            self._logger.debug("Asking for 10000 test runs starting at %i", i + 1)
            request = self._get(request_url)
            results = [] if not request else request.json()["results"]
            if not results:
                break
            test_runs = [*test_runs, *results]
            i += len(results)
        return {key: test_runs[-1][key] for key in ["key", "name"]} if test_runs else {}

    def get_test_runs(self, search_mask: str = "", **kwargs) -> List[Dict[str, str]]:
        """
        Get a list of test runs matching the search mask.

        :param search_mask: Search mask to match test runs
        :key fields: comma-separated list of fields to be included (e.g. key, name, items)

        .. note:: If fields is not set, all fields will be returned. This can be slow as it will also also include test result items.

        :returns: List of test runs
        """
        fields = kwargs.pop("fields", "")
        if kwargs:
            raise SyntaxWarning("Unknown arguments: %r", kwargs)

        # unfortunately, /testrun/search does not support empty query, so we use a basic filter here to get all test runs
        # while '<=' is supported by /testcase/search and /testplan/search it is not supported by /testrun/search (leads to http error)
        if not search_mask:
            search_mask = "folder = \"/\""

        test_runs: List = []
        i = 0
        while True:
            request_url = f"{self._adaptavist_api_url}/testrun/search?query={urllib.parse.quote_plus(search_mask)}&startAt={i}&maxResults=1000&fields={urllib.parse.quote_plus(fields)}"
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

    def create_test_run(self, project_key: str, test_run_name: str, **kwargs) -> Optional[str]:
        """
        Create a new test run.

        :param project_key: Project key of the test run ex. "TEST"
        :param test_run_name: Name of the test run to be created
        :key folder: Name of the folder where to create the new test run
        :key issue_key: Issue key to link this test run to
        :key test_plan_key: Test plan key to link this test run to
        :key test_cases: List of test case keys to be linked to the test run ex. ["TEST-T1026","TEST-T1027"]
        :key environment: Environment to distinguish multiple executions (call get_environments() to get a list of available ones)
        :key unassigned_executor: Executor and assigned to will be unassigned if true
        :return: Key of the test run created
        """
        folder: str = kwargs.pop("folder", "")
        issue_key: str = kwargs.pop("issue_key", "")
        test_plan_key: str = kwargs.pop("test_plan_key", "")
        test_cases: List[str] = kwargs.pop("test_cases", [])
        environment: str = kwargs.pop("environment", "")
        unassigned_executor: bool = kwargs.pop("unassigned_executor", False)
        if kwargs:
            raise SyntaxWarning("Unknown arguments: %r", kwargs)

        folder = ("/" + folder).replace("//", "/") if folder else ""
        # TODO: Use constants for folder_type
        if folder and folder not in self.get_folders(project_key=project_key, folder_type="TEST_RUN"):
            self.create_folder(project_key=project_key, folder_type="TEST_RUN", folder_name=folder)

        assigned_data = {} if unassigned_executor else {"executedBy": get_executor(), "assignedTo": get_executor()}
        test_cases_list_of_dicts = [
            {
                **{"testCaseKey": test_case_key, "environment": environment},
                **assigned_data,
            }
            for test_case_key in test_cases
        ]

        request_url = f"{self._adaptavist_api_url}/testrun"
        request_data = {"projectKey": project_key,
                        "testPlanKey": test_plan_key,
                        "name": test_run_name,
                        "folder": folder,
                        "issueKey": issue_key,
                        "items": test_cases_list_of_dicts}
        self._logger.debug("Creating new test run in project %s with name '%s'", test_plan_key, test_run_name)
        request = self._post(request_url, request_data)
        if request:
            response = request.json()
            return response["key"]
        return None

    def clone_test_run(self, test_run_key: str, test_run_name: str = "", **kwargs) -> Optional[str]:
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
        if kwargs:
            raise SyntaxWarning("Unknown arguments: %r", kwargs)

        test_run = self.get_test_run(test_run_key)
        if not test_run:
            return None

        test_run_items = test_run.get("items", [])

        key = self.create_test_run(project_key=project_key or test_run["projectKey"],
                                   test_run_name=test_run_name or f"{test_run['name']} (cloned from {test_run['key']})",
                                   folder=folder or test_run.get("folder"),
                                   issue_key=test_run.get("issue_key"),
                                   test_plan_key=test_plan_key,  # will be handled further below
                                   environment=environment or (test_run_items[0].get("environment") if test_run_items else None),
                                   test_cases=[item["testCaseKey"] for item in test_run_items])

        # get test plans that contain the original test run and add cloned test run to them
        if not test_plan_key:
            test_plans = self.get_test_plans()
            for test_plan in test_plans:
                test_runs: List[str] = test_plan.get("testRuns", [])
                if test_run["key"] in [item["key"] for item in test_runs]:
                    self.edit_test_plan(test_plan_key=test_plan["key"], test_runs=[key])

        return key

    def get_test_execution_results(self, last_result_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all test results.

        .. note:: This method is using JIRA API and is much faster than getting test results for each test run via Adaptavist API.
                  By simple transposing the result list it is possible to get all the results based on test run keys.

        :param last_result_only: If true, returns only the last test result of each single test execution (just like in the field 'items' of /testrun/{testRunKey}, s.a. get_test_run())
                                 If false, returns all test results, i.e. even those ones that have been overwritten (just like in /testrun/{testRunKey}/testresults, s.a. get_test_results())
        :returns: Test results
        """
        test_results: List = []
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

        results = [
            {
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
            }
            for result in test_results
            if result.get("lastTestResult", True) or not last_result_only
        ]

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
        return [] if not request else request.json()

    def create_test_results(self, test_run_key: str, results: List[Dict[str, Any]], exclude_existing_test_cases: bool = True, **kwargs) -> List[int]:
        """
        Create new test results for a given test run.

        :param test_run_key: Test run key of the result to be updated. ex. "JQA-R1234"
        :param results:
        :param exclude_existing_test_cases: If true, creates test results only for new test cases (can be used to add test cases to existing test runs)
                                            If false, creates new test results for existing test cases as well
        :key environment: environment to distinguish multiple executions (call get_environments() to get a list of available ones)
        :return: List of ids of all the test results that were created
        """
        environment: str = kwargs.pop("environment", "")
        if kwargs:
            raise SyntaxWarning("Unknown arguments: %r", kwargs)

        test_run = self.get_test_run(test_run_key)
        if not test_run:
            return []

        request_data = []
        for result in results:
            if exclude_existing_test_cases and result["testCaseKey"] in [item["testCaseKey"] for item in test_run.get("items", [])]:
                continue
            data = {key: value for key, value in result.items()}
            data["executedBy"] = get_executor()
            data["assignedTo"] = data["executedBy"]
            if environment:
                data["environment"] = environment
            request_data.append(data)

        if not request_data:
            return []

        request_url = f"{self._adaptavist_api_url}/testrun/{test_run_key}/testresults"
        self._logger.debug("Creating test results for run %s", test_run_key)
        request = self._post(request_url, request_data)
        if not request:
            return []

        response = request.json()
        return [result["id"] for result in response]

    def get_test_result(self, test_run_key: str, test_case_key: str) -> Dict[str, Any]:
        """
        Get the test result for a given test run and test case.

        :param test_run_key: Test run key of the result to be updated. ex. "JQA-R1234"
        :param test_case_key: Test case key of the result to be updated. ex. "JQA-T1234"
        :returns: Test result
        """
        request_url = f"{self._adaptavist_api_url}/testrun/{test_run_key}/testresults"
        self._logger.debug("Getting test result of %s in %s", test_case_key, test_run_key)
        request = self._get(request_url)
        response = [] if not request else request.json()
        for item in response:
            if item["testCaseKey"] == test_case_key:
                return item
        return {}

    def create_test_result(self, test_run_key: str, test_case_key: str, status: str = "", **kwargs) -> Optional[int]:
        """
        Create a new test result for a given test run and test case with the given status.

        :param test_run_key: Test run key of the result to be created. ex. "JQA-R1234"
        :param test_case_key: Test case key of the result to be created. ex. "JQA-T1234"
        :param status: Status of the result to be created. ex. "Fail"
        :key comment: Comment to add
        :key execute_time: Execution time in seconds
        :key environment: Environment to distinguish multiple executions (call get_environments() to get a list of available ones)
        :key issue_links: List of issue keys to link the test result to
        :return: ID of the test result that was created
        """
        comment: str = kwargs.pop("comment", "")
        execute_time: Optional[int] = kwargs.pop("execute_time")
        environment: str = kwargs.pop("environment", "")
        issue_links: List[str] = kwargs.pop("issue_links", [])
        if kwargs:
            raise SyntaxWarning("Unknown arguments: %r", kwargs)

        request_url = f"{self._adaptavist_api_url}/testrun/{test_run_key}/testcase/{test_case_key}/testresult"

        executor = get_executor()
        request_data: Dict[str, Any] = {
            "environment": environment,
            "executedBy": executor,
            "assignedTo": executor,
            "status": status,
        }
        if comment is not None:
            request_data["comment"] = comment
        if execute_time is not None:
            request_data["executionTime"] = execute_time * 1000
        if issue_links:
            request_data["issueLinks"] = issue_links

        self._logger.debug("Creating test result for %s in %s", test_case_key, test_run_key)
        request = self._post(request_url, request_data)
        if not request:
            return None
        response = request.json()
        return response["id"]

    def edit_test_result_status(self, test_run_key: str, test_case_key: str, status: str, **kwargs) -> Optional[int]:
        """
        Edit the last existing test result for a given test run and test case with the given status.

        :param test_run_key: Test run key of the result to be created. ex. "JQA-R1234"
        :param test_case_key: Test case key of the result to be created. ex. "JQA-T1234"
        :param status: Status of the result to be created. ex. "Fail"
        :key comment: Comment to the new status
        :key execute_time: Execution time in seconds
        :key environment: Environment to distinguish multiple executions (call get_environments() to get a list of available ones)
        :key issue_links: List of issue keys to link the test result to
        :return: ID of the test result that was created
        """
        comment: str = kwargs.pop("comment", "")
        execute_time: Optional[int] = kwargs.pop("execute_time")
        environment: str = kwargs.pop("environment", "")
        issue_links: List[str] = kwargs.pop("issue_links", [])
        if kwargs:
            raise SyntaxWarning("Unknown arguments: %r", kwargs)

        request_url = f"{self._adaptavist_api_url}/testrun/{test_run_key}/testcase/{test_case_key}/testresult"

        executor = get_executor()
        request_data: Dict[str, Any] = {
            "environment": environment,
            "executedBy": executor,
            "assignedTo": executor,
            "status": status,
        }
        if comment is not None:
            request_data["comment"] = comment
        if execute_time is not None:
            request_data["executionTime"] = execute_time * 1000
        if issue_links:
            request_data["issueLinks"] = issue_links

        self._logger.debug("Updating test result for %s in %s", test_case_key, test_run_key)
        request = self._put(request_url, request_data)
        if not request:
            return None
        response = request.json()
        return response["id"]

    def add_test_result_attachment(self, test_result_id: int, attachment: Union[str, BinaryIO], filename: str = "") -> bool:
        """
        Add attachment to a test result.

        :param test_result_id: The test result id.
        :param attachment: The attachment as filepath name or file-like object.
        :param filename: The optional filename.

        :returns: True if succeeded, False if not
        :rtype: bool
        """
        needs_to_be_closed = False
        if isinstance(attachment, str):
            try:
                attachment = open(attachment, "rb")
            except OSError as ex:
                self._logger.error("Attaching failed. %s", ex)
                return False
            needs_to_be_closed = True
        elif not filename and not attachment.name:
            self._logger.error("Attachment name is missing")
            return False
        elif hasattr(attachment, "read") and hasattr(attachment, "mode") and attachment.mode != "rb":
            self._logger.error("%s not opened in 'rb' mode, attaching file may fail", attachment.name)
            return False

        if not filename:
            filename = attachment.name

        stream = requests_toolbelt.MultipartEncoder(fields={"file": (filename, attachment, "application/octet-stream")})
        request_url = f"{self._adaptavist_api_url}/testresult/{test_result_id}/attachments"
        headers = {**self._headers}
        headers["Content-type"] = stream.content_type
        headers["X-Atlassian-Token"] = "nocheck"

        try:
            self._logger.debug("Attaching %s to %s", filename, test_result_id)
            request = requests.post(request_url,
                                    auth=self._authentication,
                                    headers=headers,
                                    data=stream)
            request.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.RequestException) as ex:
            self._logger.error("request failed. %s", ex)
            if needs_to_be_closed:
                attachment.close()
            return False

        if needs_to_be_closed:
            attachment.close()

        return True

    def edit_test_script_status(self, test_run_key: str, test_case_key: str, step: int, status: str, **kwargs) -> Optional[int]:
        """
        Edit test script result for a given test run and test case with the given status.

        :param test_run_key: Test run key of the result to be updated. ex. "JQA-R1234"
        :param test_case_key: Test case key of the result to be updated. ex. "JQA-T1234"
        :param step: Index (starting from 1) of step to be updated
        :param status: Status of the result to be updated. ex. "Fail"
        :key comment: Comment to the new status
        :key environment: Environment to distinguish multiple executions (call get_environments() to get a list of available ones)
        :return: ID of the test result that was updated
        """
        comment: str = kwargs.pop("comment", "")
        environment: str = kwargs.pop("environment", "")
        if kwargs:
            raise SyntaxWarning("Unknown arguments: %r", kwargs)

        test_result = self.get_test_result(test_run_key, test_case_key)
        script_results = test_result.get("scriptResults", [])

        for script_result in script_results:
            # keep relevant fields only (to make PUT pass)
            for key in list(script_result.keys()):
                if key not in ["index", "status", "comment"]:
                    script_result.pop(key)

            # update given step
            if script_result.get("index") == step - 1:
                script_result["status"] = status
                if comment is not None:
                    script_result["comment"] = comment

        request_url = f"{self._adaptavist_api_url}/testrun/{test_run_key}/testcase/{test_case_key}/testresult"

        executor = get_executor()
        request_data = {
            "environment": environment,
            "executedBy": executor,
            "assignedTo": executor,
            "status": test_result["status"],  # mandatory, to keep test result status unchanged
            "scriptResults": script_results,
        }

        self._logger.debug("Updating test script for %s in %s", test_case_key, test_run_key)
        request = self._put(request_url, request_data)
        if not request:
            return None
        response = request.json()
        return response["id"]

    def add_test_script_attachment(self, test_result_id: int, step: int, attachment: Union[str, BinaryIO], filename: str = "") -> bool:
        """
        Add attachment to a test script result.

        :param test_result_id: The test result id.
        :param step: Index (starting from 1) of step to be updated.
        :param attachment: The attachment as filepath name or file-like object.
        :param filename: The optional filename.
        :returns: True if succeeded, False if not
        """
        needs_to_be_closed = False
        if isinstance(attachment, str):
            try:
                attachment = open(attachment, "rb")
            except OSError as ex:
                self._logger.error("attachment failed. %s", ex)
                return False
            needs_to_be_closed = True
        elif not filename and not attachment.name:
            self._logger.error("attachment name missing")
            return False
        elif hasattr(attachment, "read") and hasattr(attachment, "mode") and attachment.mode != "rb":
            self._logger.error("%s not opened in 'rb' mode, attaching file may fail.", attachment.name)
            return False

        if not filename:
            filename = attachment.name

        stream = requests_toolbelt.MultipartEncoder(fields={"file": (filename, attachment, "application/octet-stream")})

        request_url = self._adaptavist_api_url + "/testresult/{0}/step/{1}/attachments".format(test_result_id, step - 1)
        headers = {**self._headers}
        headers["Content-type"] = stream.content_type
        headers["X-Atlassian-Token"] = "nocheck"

        try:
            request = requests.post(request_url,
                                    auth=self._authentication,
                                    headers=headers,
                                    data=stream)
            request.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.RequestException) as ex:
            self._logger.error("request failed. %s", ex)
            if needs_to_be_closed:
                attachment.close()
            return False

        if needs_to_be_closed:
            attachment.close()

        return True

    def _delete(self, request_url: str) -> Optional[requests.Response]:
        """DELETE data from Jira/Adaptavist."""
        try:
            request = requests.delete(request_url,
                                      auth=self._authentication,
                                      headers=self._headers)
            request.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.RequestException) as ex:
            self._logger.error("request failed. %s", ex)
            return None
        return request

    def _get(self, request_url: str) -> Optional[requests.Response]:
        """GET data from Jira/Adaptavist."""
        try:
            request = requests.get(request_url,
                                   auth=self._authentication,
                                   headers=self._headers)
            request.raise_for_status()
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError, requests.exceptions.RequestException) as ex:
            self._logger.error("request failed. %s", ex)
            return None
        return request

    def _post(self, request_url: str, data: Any) -> Optional[requests.Response]:
        """POST data to Jira/Adaptavist."""
        try:
            request = requests.post(request_url,
                                    auth=self._authentication,
                                    headers=self._headers,
                                    data=json.dumps(data))
            request.raise_for_status()
        except requests.exceptions.HTTPError as ex:
            # HttpPost: in case of status 400 request.text contains error messages
            self._logger.error("request failed. %s %s", ex, request.text)
            return None
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self._logger.error("request failed. %s", ex)
            return None
        return request

    def _put(self, request_url: str, data: Any) -> Optional[requests.Response]:
        """PUT data to Jira/Adaptavist."""
        try:
            request = requests.put(request_url,
                                   auth=self._authentication,
                                   headers=self._headers,
                                   data=json.dumps(data))
            request.raise_for_status()
        except requests.exceptions.HTTPError as ex:
            # HttpPut: in case of status 400 request.text contains error messages
            self._logger.error("request failed. %s %s", ex, request.text)
            return None
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self._logger.error("request failed. %s", ex)
            return None
        return request
