#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module provides functionality for Adaptavist Test Management with Jira server interaction."""

# standard
import os
import getpass
import json
import logging
import urllib.parse
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
import requests_toolbelt


class Adaptavist():
    """The Adaptavist class.

       Uses REST API of Adaptavist Test Management for Jira Server (https://docs.adaptavist.io/tm4j/server/api/) to provide its functionality .

    """

    def __init__(self, jira_server, jira_username, jira_password):
        """Construct a new Adaptavist instance."""

        self.jira_server = jira_server
        self.jira_username = jira_username
        self.jira_password = jira_password

        self.adaptavist_api_url = self.jira_server + "/rest/atm/1.0"
        self.authentication = HTTPBasicAuth(self.jira_username, self.jira_password)
        self.headers = {"Accept": "application/json", "Content-type": "application/json"}

        self.logger = logging.getLogger(self.__class__.__name__)

    def get_users(self):
        """
        Get a list of users known to Adaptavist/Jira.

        :returns: List of user keys
        :rtype: list of strings
        """
        users = []
        i = 0
        while True:
            request_url = self.jira_server + "/rest/api/2/user/search?username=.&startAt={0}&maxResults=200"

            try:
                request = requests.get(request_url.format(i),
                                       auth=self.authentication,
                                       headers=self.headers)
                request.raise_for_status()
            except HTTPError as ex:
                self.logger.error("request failed. %s", ex)
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
                self.logger.error("request failed. %s", ex)
                break

            result = [] if not request.text else request.json()
            if not result:
                break
            users = [*users, *result]
            i += len(result)

        return [user["key"] for user in users]

    def get_projects(self):
        """
        Get a list of projects known to Adatavist/Jira.

        :returns: List of projects
        :rtype: list of json data
        """

        request_url = self.jira_server + "/rest/tests/1.0/project"

        try:
            request = requests.get(request_url,
                                   auth=self.authentication,
                                   headers=self.headers)
            request.raise_for_status()
        except HTTPError as ex:
            self.logger.error("request failed. %s", ex)
            return []
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return []

        response = [] if not request.text else request.json()

        return [{"id": project["id"], "key": project["key"], "name": project["name"]} for project in response]

    def get_environments(self, project_key=None):
        """
        Get a list of environments matching the search mask.

        :param project_key: project key to search for environments
        :type project_key: str

        :returns: List of environments
        :rtype: list of json data
        """
        self.logger.debug("get_environments(\"%s\")", project_key)

        request_url = self.adaptavist_api_url + "/environments?projectKey={0}"

        try:
            request = requests.get(request_url.format(urllib.parse.quote_plus(project_key or "")),
                                   auth=self.authentication,
                                   headers=self.headers)
            request.raise_for_status()
        except HTTPError as ex:
            self.logger.error("request failed. %s", ex)
            return []
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return []

        response = [] if not request.text else request.json()

        return response

    def create_environment(self, project_key, environment_name, **kwargs):
        """
        Create a new environment.

        :param project_key: project key of the environment ex. "TEST"
        :type project_key: str
        :param environment_name: name of the environment to be created
        :type environment_name: str

        :param kwargs: Arbitrary list of keyword arguments
                description: description of the environment

        :return: id of the environment created
        :rtype: str
        """
        self.logger.debug("create_environment(\"%s\", \"%s\")", project_key, environment_name)

        description = kwargs.pop("description", None)

        assert not kwargs, "Unknown arguments: %r" % kwargs

        request_url = self.adaptavist_api_url + "/environments"

        request_data = {"projectKey": project_key,
                        "name": environment_name,
                        "description": description}

        try:
            request = requests.post(request_url,
                                    auth=self.authentication,
                                    headers=self.headers,
                                    data=json.dumps(request_data))
            request.raise_for_status()
        except HTTPError as ex:
            # HttpPost: in case of status 400 request.text contains error messages
            self.logger.error("request failed. %s %s", ex, request.text)
            return None
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return None

        response = request.json()

        return response["id"]

    def get_folders(self, project_key, folder_type):
        """
        Get a list of folders.

        :param project_key: project key to search for folders
        :type project_key: str
        :param folder_type: type of the folder to be created ("TEST_CASE", "TEST_PLAN" or "TEST_RUN")
        :type folder_type: str

        :returns: List of folders
        :rtype: list of strings
        """
        self.logger.debug("get_folders(\"%s\")", project_key)

        project_id = next((project["id"] for project in self.get_projects() if project["key"] == project_key), None)

        if not project_id:
            self.logger.error("request failed. %s", f"project {project_key} not found.")
            return []

        request_url = self.jira_server + "/rest/tests/1.0/project/{0}/foldertree/{1}?startAt={2}&maxResults=200"

        try:
            request = requests.get(request_url.format(urllib.parse.quote_plus(project_id), folder_type.replace("_", "").lower(), 0),
                                   auth=self.authentication,
                                   headers=self.headers)

            request.raise_for_status()
        except HTTPError as ex:
            self.logger.error("request failed. %s", ex)
            return []
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return []

        response = [] if not request.text else request.json()

        return build_folder_names(response)

    def create_folder(self, project_key, folder_type, folder_name, **kwargs):
        """
        Create a new environment.

        :param project_key: project key of the environment ex. "TEST"
        :type project_key: str
        :param folder_type: type of the folder to be created ("TEST_CASE", "TEST_PLAN" or "TEST_RUN")
        :type folder_type: str
        :param folder_name: name of the folder to be created
        :type folder_name: str

        :param kwargs: Arbitrary list of keyword arguments

        :return: id of the folder created
        :rtype: str
        """
        self.logger.debug("create_folder(\"%s\", \"%s\", \"%s\")", project_key, folder_type, folder_name)

        assert not kwargs, "Unknown arguments: %r" % kwargs

        request_url = self.adaptavist_api_url + "/folder"

        request_data = {"projectKey": project_key,
                        "name": folder_name,
                        "type": folder_type}

        try:
            request = requests.post(request_url,
                                    auth=self.authentication,
                                    headers=self.headers,
                                    data=json.dumps(request_data))
            request.raise_for_status()
        except HTTPError as ex:
            # HttpPost: in case of status 400 request.text contains error messages
            self.logger.error("request failed. %s %s", ex, request.text)
            return None
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return None

        response = request.json()

        return response["id"]

    def get_test_case(self, test_case_key):
        """
        Get info about a test case.

        :param test_case_key: test case key to look for
        :type test_case_key: str

        :returns: Info about test case
        :rtype: json data
        """
        self.logger.debug("get_test_case(\"%s\")", test_case_key)

        request_url = self.adaptavist_api_url + "/testcase/" + test_case_key

        try:
            request = requests.get(request_url,
                                   auth=self.authentication,
                                   headers=self.headers)
            request.raise_for_status()
        except HTTPError as ex:
            self.logger.error("request failed. %s", ex)
            return {}
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return {}

        response = {} if not request.text else request.json()

        return response

    def get_test_cases(self, search_mask=None):
        """
        Get a list of test cases matching the search mask.

        :param search_mask: search mask to match test cases
        :type search_mask: str

        :returns: List of test cases
        :rtype: list of json data
        """
        self.logger.debug("get_test_cases(\"%s\")", search_mask)

        # unfortunately, /testcase/search does not support empty query
        # so we use a basic filter here to get all test cases
        # note (2018/07/12):
        #     while '<=' is not supported by /testrun/search (leads to http error)
        #     it is supported by /testcase/search and /testplan/search
        if not search_mask:
            search_mask = "folder <= \"/\""

        test_cases = []
        i = 0
        while True:
            request_url = self.adaptavist_api_url + "/testcase/search?query={0}&startAt={1}"

            try:
                request = requests.get(request_url.format(urllib.parse.quote_plus(search_mask or ""), i),
                                       auth=self.authentication,
                                       headers=self.headers)
                request.raise_for_status()
            except HTTPError as ex:
                self.logger.error("request failed. %s", ex)
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
                self.logger.error("request failed. %s", ex)
                break

            result = [] if not request.text else request.json()
            if not result:
                break
            test_cases = [*test_cases, *result]
            i += len(result)

        return test_cases

    def edit_test_case(self, test_case_key, **kwargs):
        """
        Edit given test case.

        :param test_case_key: test case key to be edited. ex. "JQA-T1234"
        :type test_case_key: str

        :param kwargs: Arbitrary list of keyword arguments
                folder: folder to move the test case into - if not given, folder is not changed - if set to None, folder will be (re-)moved to root
                labels: list of labels to be added (add a "-" as first list entry to remove labels or to create a new list)
                build_urls: list of build urls to be added (add a "-" as first list entry to remove urls or to create a new list)
                code_bases: list of code base urls to be added (add a "-" as first list entry to remove urls or to create a new list)

        :returns: True if succeeded, False if not
        :rtype: bool
        """
        self.logger.debug("edit_test_case(\"%s\")", test_case_key)

        keep_original_value = r"\{keep_original_value\}"

        folder = kwargs.pop("folder", keep_original_value)  # differ between folder not passed and folder set to None (to move to root)
        labels = kwargs.pop("labels", None) or []
        build_urls = kwargs.pop("build_urls", [])
        code_bases = kwargs.pop("code_bases", [])

        assert not kwargs, "Unknown arguments: %r" % kwargs

        request_url = self.adaptavist_api_url + "/testcase/" + test_case_key

        try:
            request = requests.get(request_url,
                                   auth=self.authentication,
                                   headers=self.headers)
            request.raise_for_status()
        except HTTPError as ex:
            self.logger.error("request failed. %s", ex)
            return False
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return False

        response = {} if not request.text else request.json()

        request_data = {}

        folder = response.get("folder", None) if folder == keep_original_value else (("/" + folder).replace("//", "/") if folder else folder or None)
        if folder != response.get("folder", None):
            if folder and folder not in self.get_folders(project_key=response.get("projectKey"), folder_type="TEST_CASE"):
                self.create_folder(project_key=response.get("projectKey"), folder_type="TEST_CASE", folder_name=folder)
            request_data.update({"folder": folder})

        # append labels to the current list of labels or create new one
        current_values = response.get("labels", [])
        labels = update_list(current_values or [], labels)
        if labels != current_values:
            request_data.update({"labels": labels})

        # handle custom fields
        current_values = response.get("customFields", {}).get("ci_server_url", "")
        build_urls = update_multiline_field(current_values or "", build_urls)
        if build_urls != current_values:
            request_data.update({"customFields": {"ci_server_url": build_urls}})

        current_values = response.get("customFields", {}).get("code_base_url", "")
        code_bases = update_multiline_field(current_values, code_bases)
        if code_bases != current_values:
            request_data.update({"customFields": {"code_base_url": code_bases}})

        if not request_data:
            return True

        # update test case
        # according to doc only fields given in the request body are updated.

        try:
            request = requests.put(request_url,
                                   auth=self.authentication,
                                   headers=self.headers,
                                   data=json.dumps(request_data))
            request.raise_for_status()
        except HTTPError as ex:
            # HttpPut: in case of status 400 request.text contains error messages
            self.logger.error("request failed. %s %s", ex, request.text)
            return False
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return False

        return True

    def get_test_case_links(self, issue_key):
        """
        Get the list of test cases linked to an issue.

        :param issue_key: issue key to look for
        :type issue_key: str

        :returns: List of linked test cases
        :rtype: list of json data
        """
        self.logger.debug("get_test_case_links(\"%s\")", issue_key)

        request_url = self.adaptavist_api_url + "/issuelink/" + issue_key + "/testcases"

        try:
            request = requests.get(request_url,
                                   auth=self.authentication,
                                   headers=self.headers)
            request.raise_for_status()
        except HTTPError as ex:
            self.logger.error("request failed. %s", ex)
            return []
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return []

        response = [] if not request.text else request.json()

        return response

    def link_test_cases(self, issue_key, test_case_keys):
        """
        Links a list of existing testcases to an issue.

        :param issue_key: issue to link the test cases to
        :type issue_key: str
        :param test_case_keys: list of test case keys to be linked to the issue
        :type test_case_keys: list(str)

        :returns: True if succeeded, False if not
        :rtype: bool
        """
        self.logger.debug("link_test_cases(\"%s\", \"%s\")", issue_key, test_case_keys)

        for test_case_key in test_case_keys:
            request_url = self.adaptavist_api_url + "/testcase/" + test_case_key

            try:
                request = requests.get(request_url,
                                       auth=self.authentication,
                                       headers=self.headers)
                request.raise_for_status()
            except HTTPError as ex:
                if request.status_code == 404 and not request.text:
                    # ignore errors (e.g. test case unknown or not found) and try next test case
                    pass
                else:
                    self.logger.error("request failed. %s", ex)
                    return False
            except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
                self.logger.error("request failed. %s", ex)
                return False

            response = {} if not request.text else request.json()

            update_needed = False

            # append issue to the current list of issue links
            issue_links = response.get("issueLinks", [])
            if issue_key not in issue_links:
                issue_links.append(issue_key)
                update_needed = True

                if not update_needed:
                    continue

                # update list of issue links
                # according to doc only fields given in the request body are updated.
                request_data = {"issueLinks": issue_links}

                try:
                    request = requests.put(request_url,
                                           auth=self.authentication,
                                           headers=self.headers,
                                           data=json.dumps(request_data))
                    request.raise_for_status()
                except HTTPError as ex:
                    # HttpPut: in case of status 400 request.text contains error messages
                    self.logger.error("request failed. %s %s", ex, request.text)
                    return False
                except (requests.exceptions.ConnectionError, requests.exceptions.RequestException):
                    self.logger.error("request failed. %s", ex)
                    return False

        return True

    def unlink_test_cases(self, issue_key, test_case_keys):
        """
        Unlink a list of existing testcases from an issue.

        :param issue_key: issue to unlink the test cases from
        :type issue_key: str
        :param test_case_keys: list of test case keys to be unlinked from the issue
        :type test_case_keys: list(str)

        :returns: True if succeeded, False if not
        :rtype: bool
        """
        self.logger.debug("unlink_test_cases(\"%s\", \"%s\")", issue_key, test_case_keys)

        for test_case_key in test_case_keys:
            request_url = self.adaptavist_api_url + "/testcase/" + test_case_key

            try:
                request = requests.get(request_url,
                                       auth=self.authentication,
                                       headers=self.headers)
                request.raise_for_status()
            except HTTPError as ex:
                if request.status_code == 404 and not request.text:
                    # ignore errors (e.g. test case unknown or not found) and try next test case
                    pass
                else:
                    self.logger.debug("request failed. %s", ex)
                    return False
            except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
                self.logger.debug("request failed. %s", ex)
                return False

            response = {} if not request.text else request.json()

            update_needed = False

            # remove issue from the current list of issue links
            issue_links = response.get("issueLinks", [])
            if issue_key in issue_links:
                issue_links.remove(issue_key)
                update_needed = True

                if not update_needed:
                    continue

                # update list of issue links
                # according to doc only fields given in the request body are updated.
                request_data = {"issueLinks": issue_links}

                try:
                    request = requests.put(request_url,
                                           auth=self.authentication,
                                           headers=self.headers,
                                           data=json.dumps(request_data))
                    request.raise_for_status()
                except HTTPError as ex:
                    # HttpPut: in case of status 400 request.text contains error messages
                    self.logger.error("request failed. %s %s", ex, request.text)
                    return False
                except (requests.exceptions.ConnectionError, requests.exceptions.RequestException):
                    self.logger.error("request failed. %s", ex)
                    return False

        return True

    def get_test_plan(self, test_plan_key):
        """
        Get info about a test plan.

        :param test_plan_key: test plan key to look for
        :type test_plan_key: str

        :returns: Info about test plan
        :rtype: json data
        """
        self.logger.debug("get_test_plan(\"%s\")", test_plan_key)

        request_url = self.adaptavist_api_url + "/testplan/" + test_plan_key

        try:
            request = requests.get(request_url,
                                   auth=self.authentication,
                                   headers=self.headers)
            request.raise_for_status()
        except HTTPError as ex:
            self.logger.error("request failed. %s", ex)
            return {}
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return {}

        response = {} if not request.text else request.json()

        return response

    def get_test_plans(self, search_mask=None):
        """
        Get a list of test plans matching the search mask.

        :param search_mask: search mask to match test plans
        :type search_mask: str

        :returns: List of test plans
        :rtype: list of json data
        """
        self.logger.debug("get_test_plans(\"%s\")", search_mask)

        # unfortunately, /testplan/search does not support empty query
        # so we use a basic filter here to get all test plans
        # note (2018/07/12):
        #     while '<=' is not supported by /testrun/search (leads to http error)
        #     it is supported by /testcase/search and /testplan/search
        #     however, using '=' does not to get all test plans, but '<=' does
        if not search_mask:
            search_mask = "folder <= \"/\""

        test_plans = []
        i = 0
        while True:
            request_url = self.adaptavist_api_url + "/testplan/search?query={0}&startAt={1}"

            try:
                request = requests.get(request_url.format(urllib.parse.quote_plus(search_mask or ""), i),
                                       auth=self.authentication,
                                       headers=self.headers)
                request.raise_for_status()
            except HTTPError as ex:
                self.logger.error("request failed. %s", ex)
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
                self.logger.error("request failed. %s", ex)
                break

            result = [] if not request.text else request.json()
            if not result:
                break
            test_plans = [*test_plans, *result]
            i += len(result)

        return test_plans

    def create_test_plan(self, project_key, test_plan_name, **kwargs):
        """
        Create a new test plan.

        :param project_key: project key of the test plan ex. "TEST"
        :type project_key: str
        :param test_plan_name: name of the test plan to be created
        :type test_plan_name: str

        :param kwargs: Arbitrary list of keyword arguments
                folder: name of the folder where to create the new test plan
                issue_links: list of issue keys to link the new test plan to
                test_runs: list of test run keys to be linked to the test plan ex. ["TEST-R2","TEST-R7"]

        :return: key of the test plan created
        :rtype: str
        """
        self.logger.debug("create_test_plan(\"%s\", \"%s\")", project_key, test_plan_name)

        folder = kwargs.pop("folder", None)
        issue_links = kwargs.pop("issue_links", None) or []
        test_runs = kwargs.pop("test_runs", None) or []

        assert not kwargs, "Unknown arguments: %r" % kwargs

        folder = ("/" + folder).replace("//", "/") if folder else folder or None
        if folder and folder not in self.get_folders(project_key=project_key, folder_type="TEST_PLAN"):
            self.create_folder(project_key=project_key, folder_type="TEST_PLAN", folder_name=folder)

        request_url = self.adaptavist_api_url + "/testplan"

        request_data = {"projectKey": project_key,
                        "name": test_plan_name,
                        "folder": folder,
                        "status": "Approved",
                        "issueLinks": [x.strip() for x in issue_links.split(",")] if isinstance(issue_links, str) else issue_links,
                        "testRunKeys": [x.strip() for x in test_runs.split(",")] if isinstance(test_runs, str) else test_runs}

        try:
            request = requests.post(request_url,
                                    auth=self.authentication,
                                    headers=self.headers,
                                    data=json.dumps(request_data))
            request.raise_for_status()
        except HTTPError as ex:
            # HttpPost: in case of status 400 request.text contains error messages
            self.logger.error("request failed. %s %s", ex, request.text)
            return None
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return None

        response = request.json()

        return response["key"]

    def edit_test_plan(self, test_plan_key, **kwargs):
        """
        Edit given test plan.

        :param test_plan_key: test plan key to be edited. ex. "JQA-P1234"
        :type test_plan_key: str

        :param kwargs: Arbitrary list of keyword arguments
                folder: folder to move the test plan into
                issue_links: list of issue keys to link the new test plan to
                test_runs: list of test run keys to be linked/added to the test plan ex. ["TEST-R2","TEST-R7"]

        :returns: True if succeeded, False if not
        :rtype: bool
        """
        self.logger.debug("edit_test_plan(\"%s\")", test_plan_key)

        keep_original_value = r"\{keep_original_value\}"

        folder = kwargs.pop("folder", keep_original_value)  # differ between folder not passed and folder set to None (to move to root)
        issue_links = kwargs.pop("issue_links", None) or []
        test_runs = kwargs.pop("test_runs", None) or []

        assert not kwargs, "Unknown arguments: %r" % kwargs

        request_url = self.adaptavist_api_url + "/testplan/" + test_plan_key

        try:
            request = requests.get(request_url,
                                   auth=self.authentication,
                                   headers=self.headers)
            request.raise_for_status()
        except HTTPError as ex:
            self.logger.error("request failed. %s", ex)
            return False
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return False

        response = {} if not request.text else request.json()

        request_data = {}

        folder = response.get("folder", None) if folder == keep_original_value else (("/" + folder).replace("//", "/") if folder else folder or None)
        if folder != response.get("folder", None):
            if folder and folder not in self.get_folders(project_key=response.get("projectKey"), folder_type="TEST_PLAN"):
                self.create_folder(project_key=response.get("projectKey"), folder_type="TEST_PLAN", folder_name=folder)
            request_data.update({"folder": folder})

        # append test runs to the current list of test runs or create new ones
        current_values = [test_run["key"] for test_run in response.get("testRuns", [])]
        test_runs = update_list(current_values or [], test_runs)
        if test_runs != current_values:
            request_data.update({"testRuns": test_runs})

        # append issue links to the current list of issue links or create new ones
        current_values = response.get("issueLinks", [])
        issue_links = update_list(current_values or [], issue_links)
        if issue_links != current_values:
            request_data.update({"issueLinks": issue_links})

        if not request_data:
            return True

        # update test plan
        # according to doc only fields given in the request body are updated.

        try:
            request = requests.put(request_url,
                                   auth=self.authentication,
                                   headers=self.headers,
                                   data=json.dumps(request_data))
            request.raise_for_status()
        except HTTPError as ex:
            # HttpPut: in case of status 400 request.text contains error messages
            self.logger.error("request failed. %s %s", ex, request.text)
            return False
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return False

        return True

    def get_test_run(self, test_run_key):
        """
        Get info about a test run.

        :param test_run_key: test run key to look for
        :type test_run_key: str

        :returns: Info about test run
        :rtype: json data
        """
        self.logger.debug("get_test_run(\"%s\")", test_run_key)

        request_url = self.adaptavist_api_url + "/testrun/" + test_run_key

        try:
            request = requests.get(request_url,
                                   auth=self.authentication,
                                   headers=self.headers)
            request.raise_for_status()
        except HTTPError as ex:
            self.logger.debug("request failed. %s", ex)
            return {}
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return {}

        response = {} if not request.text else request.json()

        return response

    def get_test_run_by_name(self, test_run_name):
        """
        Get info about a test run (last one found by name).

        Note:
        This method is using JIRA API as Adaptavist API does not support this properly (would be too slow to get this info).

        :param test_run_name: test run name to look for
        :type test_run_name: str

        :returns: Info about test run
        :rtype: json data
        """
        self.logger.debug("get_test_run_by_name(\"%s\")", test_run_name)

        test_runs = []
        i = 0
        while True:
            search_mask = "testRun.name = \"{0}\"".format(test_run_name)
            request_url = self.jira_server + "/rest/tests/1.0/testrun/search?startAt={0}&maxResults=10000&query={1}&fields=id,key,name"

            try:
                request = requests.get(request_url.format(i, urllib.parse.quote_plus(search_mask or "")),
                                       auth=self.authentication,
                                       headers=self.headers)
                request.raise_for_status()
            except HTTPError as ex:
                self.logger.error("request failed. %s", ex)
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
                self.logger.error("request failed. %s", ex)
                break

            results = [] if not request.text else request.json()["results"]
            if not results:
                break
            test_runs = [*test_runs, *results]
            i += len(results)

        return {key: test_runs[-1][key] for key in ["key", "name"]} if test_runs else {}

    def get_test_runs(self, search_mask=None, **kwargs):
        """
        Get a list of test runs matching the search mask.

        :param search_mask: search mask to match test runs
        :type search_mask: str

        :param kwargs: Arbitrary list of keyword arguments
                fields: comma-separated list of fields to be included (e.g. key, name, items)
                        note: if not set, all fields will be returned, can be slow as it will also also include test result items

        :returns: List of test runs
        :rtype: list of json data
        """
        self.logger.debug("get_test_runs(\"%s\")", search_mask)

        fields = kwargs.pop("fields", None)

        assert not kwargs, "Unknown arguments: %r" % kwargs

        # unfortunately, /testrun/search does not support empty query
        # so we use a basic filter here to get all test runs
        # note (2018/07/12):
        #     while '<=' is supported by /testcase/search and /testplan/search
        #     it is not supported by /testrun/search (leads to http error)
        #     however, using '=' seems to be enough to get all test runs
        if not search_mask:
            search_mask = "folder = \"/\""

        test_runs = []
        i = 0
        while True:
            request_url = self.adaptavist_api_url + "/testrun/search?query={0}&startAt={1}&maxResults=1000&fields={2}"

            try:
                request = requests.get(request_url.format(urllib.parse.quote_plus(search_mask or ""), i, urllib.parse.quote_plus(fields or "")),
                                       auth=self.authentication,
                                       headers=self.headers)
                request.raise_for_status()
            except HTTPError as ex:
                self.logger.debug("request failed. %s", ex)
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
                self.logger.error("request failed. %s", ex)
                break

            result = [] if not request.text else request.json()
            if not result:
                break
            test_runs = [*test_runs, *result]
            i += len(result)

        return test_runs

    def get_test_run_links(self, issue_key):
        """
        Get a list of test runs linked to an issue.

        :param issue_key: issue key to look for
        :type issue_key: str

        :returns: List of linked test runs
        :rtype: list of json data
        """
        self.logger.debug("get_test_run_links(\"%s\")", issue_key)

        test_runs = self.get_test_runs()

        return [test_run for test_run in test_runs if test_run.get("issueKey") == issue_key]

    def create_test_run(self, project_key, test_run_name, **kwargs):
        """
        Create a new test run.

        :param project_key: project key of the test run ex. "TEST"
        :type project_key: str
        :param test_run_name: name of the test run to be created
        :type test_run_name: str

        :param kwargs: Arbitrary list of keyword arguments
                folder: name of the folder where to create the new test run
                issue_key: issue key to link this test run to
                test_plan_key: test plan key to link this test run to
                test_cases: list of test case keys to be linked to the test run ex. ["TEST-T1026","TEST-T1027"]
                environment: environment to distinguish multiple executions (call get_environments() to get a list of available ones)

        :return: key of the test run created
        :rtype: str
        """
        self.logger.debug("create_test_run(\"%s\", \"%s\")", project_key, test_run_name)

        folder = kwargs.pop("folder", None)
        issue_key = kwargs.pop("issue_key", None)
        test_plan_key = kwargs.pop("test_plan_key", None)
        test_cases = kwargs.pop("test_cases", [])
        environment = kwargs.pop("environment", None)

        assert not kwargs, "Unknown arguments: %r" % kwargs

        folder = ("/" + folder).replace("//", "/") if folder else folder or None
        if folder and folder not in self.get_folders(project_key=project_key, folder_type="TEST_RUN"):
            self.create_folder(project_key=project_key, folder_type="TEST_RUN", folder_name=folder)

        test_cases_list_of_dicts = []
        for test_case_key in test_cases:
            test_cases_list_of_dicts.append({"testCaseKey": test_case_key, "environment": environment, "executedBy": get_executor()})

        request_url = self.adaptavist_api_url + "/testrun"

        request_data = {"projectKey": project_key,
                        "testPlanKey": test_plan_key,
                        "name": test_run_name,
                        "folder": folder,
                        "issueKey": issue_key,
                        "items": test_cases_list_of_dicts}

        try:
            request = requests.post(request_url,
                                    auth=self.authentication,
                                    headers=self.headers,
                                    data=json.dumps(request_data))
            request.raise_for_status()
        except HTTPError as ex:
            # HttpPost: in case of status 400 request.text contains error messages
            self.logger.error("request failed. %s %s", ex, request.text)
            return None
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return None

        response = request.json()

        return response["key"]

    def clone_test_run(self, test_run_key, test_run_name=None, **kwargs):
        """
        Clone a given test run.

        :param test_run_key: test run key to be cloned
        :type test_run_key: str
        :param test_run_name: name of the test run clone (if empty, original name is used with appropriate suffix)
        :type test_run_name: str

        :param kwargs: Arbitrary list of keyword arguments
                folder: name of the folder where to create the new test run
                test_plan_key: test plan key to link this test run to
                environment: environment to distinguish multiple executions (call get_environments() to get a list of available ones)

        :return: key of the test run clone
        :rtype: str
        """
        self.logger.debug("clone_test_run(\"%s\", \"%s\")", test_run_key, test_run_name)

        folder = kwargs.pop("folder", None)
        test_plan_key = kwargs.pop("test_plan_key", None)
        project_key = kwargs.pop("project_key", None)
        environment = kwargs.pop("environment", None)

        assert not kwargs, "Unknown arguments: %r" % kwargs

        test_run = self.get_test_run(test_run_key)

        if not test_run:
            return None

        test_run_items = test_run.get("items", [])

        key = self.create_test_run(project_key=project_key or test_run["projectKey"],
                                   test_run_name=test_run_name or f"{test_run['name']} (cloned from {test_run['key']})",
                                   folder=folder or test_run.get("folder", None),
                                   issue_key=test_run.get("issue_key", None),
                                   test_plan_key=test_plan_key,  # will be handled further below
                                   # version=test_run.get("version", None),
                                   # iteration=test_run.get("iteration", None),
                                   # owner=test_run.get("owner", None),
                                   environment=environment or ((test_run_items[0].get("environment", None) if test_run_items else None)),
                                   test_cases=[item["testCaseKey"] for item in test_run_items])

        # get test plans that contain the original test run and add cloned test run to them
        if not test_plan_key:
            test_plans = self.get_test_plans()
            for test_plan in test_plans:
                test_runs = test_plan.get("testRuns", [])
                if test_run["key"] in [item["key"] for item in test_runs]:
                    self.edit_test_plan(test_plan_key=test_plan["key"], test_runs=[key])

        return key

    def get_test_execution_results(self, last_result_only=True):
        """
        Get all test results.

        Note:
        This method is using JIRA API and is much faster than getting test results for each test run via Adaptavist API.
        By simple transposing the result list it is possible to get all the results based on test run keys.

        :param last_result_only: if true, returns only the last test result of each single test execution (just like in the field 'items' of /testrun/{testRunKey}, s.a. get_test_run())
                                 if false, returns all test results, i.e. even those ones that have been overwritten (just like in /testrun/{testRunKey}/testresults, s.a. get_test_results())
        :type last_result_only: bool

        :returns: test results
        :rtype: list of json data
        """
        self.logger.debug("get_test_execution_results()")

        test_results = []
        i = 0
        while True:
            request_url = self.jira_server + "/rest/tests/1.0/reports/testresults?startAt={0}&maxResults=10000"

            try:
                request = requests.get(request_url.format(i),
                                       auth=self.authentication,
                                       headers=self.headers)
                request.raise_for_status()
            except HTTPError as ex:
                self.logger.error("request failed. %s", ex)
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
                self.logger.error("request failed. %s", ex)
                break

            results = [] if not request.text else request.json()["results"]
            if not results:
                break
            test_results = [*test_results, *results]
            i += len(results)

        results = []
        for result in test_results:
            if result.get("lastTestResult", True) or not last_result_only:
                results.append(
                    {
                        "key": result["key"],
                        "testCase": result.get("testCase", {}),
                        "testRun": result.get("testRun", {}),
                        "estimatedTime": result.get("estimatedTime", None),
                        "executedBy": result["user"].get("key", None),
                        "executionDate": result.get("executionDate", None),
                        "executionTime": result.get("executionTime", None),
                        "environment": result.get("environment", {}).get("name", None),
                        "assignedTo": result.get("assignedTo", None),
                        "automated": result.get("automated", False),
                        "status": result["status"]["name"],
                        "issueLinks": result.get("issues", [])
                    }
                )

        return results

    def get_test_results(self, test_run_key):
        """
        Get all test results for a given test run.

        :param test_run_key: test run key of the result to be updated. ex. "JQA-R1234"
        :type test_run_key: str

        :returns: test results
        :rtype: list of json data
        """
        self.logger.debug("get_test_results(\"%s\")", test_run_key)

        request_url = self.adaptavist_api_url + "/testrun/" + test_run_key + "/testresults"

        try:
            request = requests.get(request_url,
                                   auth=self.authentication,
                                   headers=self.headers)
            request.raise_for_status()
        except HTTPError as ex:
            if request.status_code == 404 and not request.text:
                # ignore errors (e.g. test run unknown or not found)
                pass
            else:
                self.logger.error("request failed. %s", ex)
                return []
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return []

        response = [] if not request.text else request.json()

        return response

    def create_test_results(self, test_run_key, results, exclude_existing_test_cases=True, **kwargs):
        """
        Create new test results for a given test run.

        :param test_run_key: test run key of the result to be updated. ex. "JQA-R1234"
        :type test_run_key: str
        :param exclude_existing_test_cases: if true, creates test results only for new test cases (can be used to add test cases to existing test runs)
                                            if false, creates new test results for existing test cases as well
        :type exclude_existing_test_cases: bool

        :param kwargs: Arbitrary list of keyword arguments
                environment: environment to distinguish multiple executions (call get_environments() to get a list of available ones)
                             sets environment field for all test cases

        :return: list of ids of all the test results that were created
        :rtype: list of ints
        """
        self.logger.debug("create_test_results(\"%s\")", test_run_key)

        environment = kwargs.pop("environment", None)

        assert not kwargs, "Unknown arguments: %r" % kwargs

        test_run = self.get_test_run(test_run_key)

        if not test_run:
            return None

        request_url = self.adaptavist_api_url + "/testrun/" + test_run_key + "/testresults"

        request_data = []
        for result in results:
            if exclude_existing_test_cases and result["testCaseKey"] in [item["testCaseKey"] for item in test_run.get("items", [])]:
                continue
            data = {key: value for key, value in result.items()}
            data["executedBy"] = get_executor()
            if environment:
                data["environment"] = environment
            request_data.append(data)

        if not request_data:
            return []

        try:
            request = requests.post(request_url,
                                    auth=self.authentication,
                                    headers=self.headers,
                                    data=json.dumps(request_data))
            request.raise_for_status()
        except HTTPError as ex:
            # HttpPost: in case of status 400 request.text contains error messages
            self.logger.error("request failed. %s %s", ex, request.text)
            return []
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return []

        response = request.json()

        return [result["id"] for result in response]

    def get_test_result(self, test_run_key, test_case_key):
        """
        Get the test result for a given test run and test case.

        :param test_run_key: test run key of the result to be updated. ex. "JQA-R1234"
        :type test_run_key: str
        :param test_case_key: test case key of the result to be updated. ex. "JQA-T1234"
        :type test_case_key: str

        :returns: test result
        :rtype: json data
        """
        self.logger.debug("get_test_result(\"%s\", \"%s\")", test_run_key, test_case_key)

        request_url = self.adaptavist_api_url + "/testrun/" + test_run_key + "/testresults"

        try:
            request = requests.get(request_url,
                                   auth=self.authentication,
                                   headers=self.headers)
            request.raise_for_status()
        except HTTPError as ex:
            if request.status_code == 404 and not request.text:
                # ignore errors (e.g. test run unknown or not found)
                pass
            else:
                self.logger.error("request failed. %s", ex)
                return {}
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return {}

        response = [] if not request.text else request.json()

        test_result = {}
        for item in response:
            if item["testCaseKey"] == test_case_key:
                test_result = item
                break

        return test_result

    def create_test_result(self, test_run_key, test_case_key, status=None, **kwargs):
        """
        Create a new test result for a given test run and test case with the given status.

        :param test_run_key: test run key of the result to be created. ex. "JQA-R1234"
        :type test_run_key: str
        :param test_case_key: test case key of the result to be created. ex. "JQA-T1234"
        :type test_case_key: str
        :param status: status of the result to be created. ex. "Fail"
        :type status: str

        :param kwargs: Arbitrary list of keyword arguments
                comment: comment to add
                execute_time: execution time in seconds. ex. "5"
                environment: environment to distinguish multiple executions (call get_environments() to get a list of available ones)
                issue_links: list of issue keys to link the test result to

        :return: id of the test result that was created
        :rtype: int
        """
        self.logger.debug("create_test_result(\"%s\", \"%s\", \"%s\")", test_run_key, test_case_key, status)

        comment = kwargs.pop("comment", None)
        execute_time = kwargs.pop("execute_time", None)
        environment = kwargs.pop("environment", None)
        issue_links = kwargs.pop("issue_links", None) or []

        assert not kwargs, "Unknown arguments: %r" % kwargs

        request_url = self.adaptavist_api_url + "/testrun/" + test_run_key + "/testcase/" + test_case_key + "/testresult"

        request_data = {}
        request_data["environment"] = environment
        request_data["executedBy"] = get_executor()
        request_data["status"] = status
        if comment is not None:
            request_data["comment"] = comment
        if execute_time is not None:
            request_data["executionTime"] = execute_time * 1000
        if issue_links:
            request_data["issueLinks"] = [x.strip() for x in issue_links.split(",")] if isinstance(issue_links, str) else issue_links

        try:
            request = requests.post(request_url,
                                    auth=self.authentication,
                                    headers=self.headers,
                                    data=json.dumps(request_data))
            request.raise_for_status()
        except HTTPError as ex:
            # HttpPost: in case of status 400 request.text contains error messages
            self.logger.error("request failed. %s %s", ex, request.text)
            return None
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return None

        response = request.json()

        return response["id"]

    def edit_test_result_status(self, test_run_key, test_case_key, status, **kwargs):
        """
        Edit the last existing test result for a given test run and test case with the given status.

        :param test_run_key: test run key of the result to be created. ex. "JQA-R1234"
        :type test_run_key: str
        :param test_case_key: test case key of the result to be created. ex. "JQA-T1234"
        :type test_case_key: str
        :param status: status of the result to be created. ex. "Fail"
        :type status: str

        :param kwargs: Arbitrary list of keyword arguments
                comment: comment to the new status
                execute_time: execution time in seconds. ex. "5"
                environment: environment to distinguish multiple executions (call get_environments() to get a list of available ones)
                issue_links: list of issue keys to link the test result to

        :return: id of the test result that was created
        :rtype: int
        """
        if not test_run_key:
            raise ValueError("test_run_key not set")

        if not test_case_key:
            raise ValueError("test_case_key not set")

        if not status:
            raise ValueError("status not set")

        self.logger.debug("edit_test_result_status(\"%s\", \"%s\", \"%s\")", test_run_key, test_case_key, status)

        comment = kwargs.pop("comment", None)
        execute_time = kwargs.pop("execute_time", None)
        environment = kwargs.pop("environment", None)
        issue_links = kwargs.pop("issue_links", None) or []

        assert not kwargs, "Unknown arguments: %r" % kwargs

        request_url = self.adaptavist_api_url + "/testrun/" + test_run_key + "/testcase/" + test_case_key + "/testresult"

        request_data = {}
        request_data["environment"] = environment
        request_data["executedBy"] = get_executor()
        request_data["status"] = status
        if comment is not None:
            request_data["comment"] = comment
        if execute_time is not None:
            request_data["executionTime"] = execute_time * 1000
        if issue_links:
            request_data["issueLinks"] = [x.strip() for x in issue_links.split(",")] if isinstance(issue_links, str) else issue_links

        try:
            request = requests.put(request_url,
                                   auth=self.authentication,
                                   headers=self.headers,
                                   data=json.dumps(request_data))
            request.raise_for_status()
        except HTTPError as ex:
            # HttpPut: in case of status 400 request.text contains error messages
            self.logger.error("request failed. %s %s", ex, request.text)
            return None
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return None

        response = request.json()

        return response["id"]

    def add_test_result_attachment(self, test_result_id, attachment, filename=None):
        """
        Add attachment to a test result.

        :param test_result_id: The test result id.
        :type test_result_id: int
        :param attachment: The attachment as filepath name or file-like object.
        :param filename: The optional filename.

        :returns: True if succeeded, False if not
        :rtype: bool
        """
        self.logger.debug("add_test_result_attachment(\"%s\", \"%s\", \"%s\")", test_result_id, attachment, filename)

        needs_to_be_closed = False
        if isinstance(attachment, str):
            try:
                attachment = open(attachment, "rb")
            except OSError as ex:
                self.logger.error("attachment failed. %s", ex)
                return False
            needs_to_be_closed = True
        elif not filename and not attachment.name:
            self.logger.error("attachment name missing")
            return False
        elif hasattr(attachment, "read") and hasattr(attachment, "mode") and attachment.mode != "rb":
            self.logger.error("%s not opened in 'rb' mode, attaching file may fail.", attachment.name)
            return False

        if not filename:
            filename = attachment.name

        stream = requests_toolbelt.MultipartEncoder(fields={"file": (filename, attachment, "application/octet-stream")})

        request_url = self.adaptavist_api_url + "/testresult/{0}/attachments".format(test_result_id)
        headers = {**self.headers}
        headers["Content-type"] = stream.content_type
        headers["X-Atlassian-Token"] = "nocheck"

        try:
            request = requests.post(request_url,
                                    auth=self.authentication,
                                    headers=headers,
                                    data=stream)
            request.raise_for_status()
        except HTTPError as ex:
            self.logger.error("request failed. %s", ex)
            if needs_to_be_closed:
                attachment.close()
            return False
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            if needs_to_be_closed:
                attachment.close()
            return False

        if needs_to_be_closed:
            attachment.close()

        return True

    def edit_test_script_status(self, test_run_key, test_case_key, step, status, **kwargs):
        """
        Edit test script result for a given test run and test case with the given status.

        :param test_run_key: test run key of the result to be updated. ex. "JQA-R1234"
        :type test_run_key: str
        :param test_case_key: test case key of the result to be updated. ex. "JQA-T1234"
        :type test_case_key: str
        :param step: index (starting from 1) of step to be updated. ex. 1
        :type step: int
        :param status: status of the result to be updated. ex. "Fail"
        :type status: str

        :param kwargs: Arbitrary list of keyword arguments
                comment: comment to the new status
                environment: environment to distinguish multiple executions (call get_environments() to get a list of available ones)

        :return: id of the test result that was updated
        :rtype: int
        """
        self.logger.debug("edit_test_script_status(\"%s\", \"%s\", \"%i\", \"%s\")", test_run_key, test_case_key, step, status)

        comment = kwargs.pop("comment", None)
        environment = kwargs.pop("environment", None)

        assert not kwargs, "Unknown arguments: %r" % kwargs

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

        request_url = self.adaptavist_api_url + "/testrun/" + test_run_key + "/testcase/" + test_case_key + "/testresult"

        request_data = {}
        request_data["environment"] = environment
        request_data["executedBy"] = get_executor()
        request_data["status"] = test_result.get("status")  # mandatory, to keep test result status unchanged
        request_data["scriptResults"] = script_results

        try:
            request = requests.put(request_url,
                                   auth=self.authentication,
                                   headers=self.headers,
                                   data=json.dumps(request_data))
            request.raise_for_status()
        except HTTPError as ex:
            # HttpPut: in case of status 400 request.text contains error messages
            self.logger.error("request failed. %s %s", ex, request.text)
            return None
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            return None

        response = request.json()

        return response["id"]

    def add_test_script_attachment(self, test_result_id, step, attachment, filename=None):
        """
        Add attachment to a test script result.

        :param test_result_id: The test result id.
        :type test_result_id: int
        :param step: index (starting from 1) of step to be updated. ex. 1
        :type step: int
        :param attachment: The attachment as filepath name or file-like object.
        :param filename: The optional filename.

        :returns: True if succeeded, False if not
        :rtype: bool
        """
        self.logger.debug("add_test_script_attachment(\"%s\", \"%i\", \"%s\", \"%s\")", test_result_id, step, attachment, filename)

        needs_to_be_closed = False
        if isinstance(attachment, str):
            try:
                attachment = open(attachment, "rb")
            except OSError as ex:
                self.logger.error("attachment failed. %s", ex)
                return False
            needs_to_be_closed = True
        elif not filename and not attachment.name:
            self.logger.error("attachment name missing")
            return False
        elif hasattr(attachment, "read") and hasattr(attachment, "mode") and attachment.mode != "rb":
            self.logger.error("%s not opened in 'rb' mode, attaching file may fail.", attachment.name)
            return False

        if not filename:
            filename = attachment.name

        stream = requests_toolbelt.MultipartEncoder(fields={"file": (filename, attachment, "application/octet-stream")})

        request_url = self.adaptavist_api_url + "/testresult/{0}/step/{1}/attachments".format(test_result_id, step - 1)
        headers = {**self.headers}
        headers["Content-type"] = stream.content_type
        headers["X-Atlassian-Token"] = "nocheck"

        try:
            request = requests.post(request_url,
                                    auth=self.authentication,
                                    headers=headers,
                                    data=stream)
            request.raise_for_status()
        except HTTPError as ex:
            self.logger.error("request failed. %s", ex)
            if needs_to_be_closed:
                attachment.close()
            return False
        except (requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
            self.logger.error("request failed. %s", ex)
            if needs_to_be_closed:
                attachment.close()
            return False

        if needs_to_be_closed:
            attachment.close()

        return True


# -------------------- helper methods --------------------
def get_executor():
    """Get executor name."""
    build_url = os.environ.get("BUILD_URL", None)
    jenkins_url = os.environ.get("JENKINS_URL", None)
    is_jenkins = build_url and jenkins_url and build_url.startswith(jenkins_url)
    return "jenkins" if is_jenkins else getpass.getuser().lower()


def build_folder_names(result, folder_name=None):
    """Build list of folder names from a hierarchical dictionary."""

    folders = []

    folder_name = "/".join((folder_name or "", result.get("name", ""))).replace("//", "/")
    folders.append(folder_name)

    if not result.get("children", []):
        return folders

    for child in result["children"]:
        folders.extend(build_folder_names(child, folder_name))

    return folders


def update_list(content, new_values):
    """Update a list with additional or new values."""
    new_content = content[:] if content else []
    new_values = [x.strip() for x in new_values.split(",")] if isinstance(new_values, str) else new_values or []
    for value in new_values:
        if value == "-":
            new_content.clear()
        elif value and value not in new_content:
            new_content.append(value)
    return new_content


def update_multiline_field(content, new_values):
    """Update a multine custom field (html) with additional or new values."""
    new_content = content[:] if content else ""
    new_values = [x.strip() for x in new_values.split(",")] if isinstance(new_values, str) else new_values or []
    for value in new_values:
        if value == "-":
            new_content = ""
        elif value and value not in new_content:
            new_content = value if not new_content else new_content + "<br>" + value
    return new_content
