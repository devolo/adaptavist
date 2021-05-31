# adaptavist

This python package provides functionality for Jira Test Management ([tm4j](https://www.adaptavist.com/doco/display/KT/Managing+Tests+From+the+REST+API)).

## Table of Contents

- [Installation](#installation)
- [Getting Started](#getting-started)
- [Examples and Features](#examples-and-features)
- [General Workflow](#general-workflow)

## Installation

To install adaptavist, you can use the following command(s):

```bash
python -m pip install adaptavist
```

To uninstall adaptavist, you can use the following command:

```bash
python -m pip uninstall adaptavist
```

## Getting Started

adaptavist is using the REST API of Adaptavist Test Management for Jira Server (see https://docs.adaptavist.io/tm4j/server/api/) and Jira's internal REST API, both with HTTP Basic authentication.

In order to access Adaptavist/Jira, valid credentials are necessary. In addition, `getpass.getuser().lower()` must be a known Jira user as well.

## Examples and Features

### General Workflow

   ```python
    from adaptavist import Adaptavist

    # create a new instance
    atm = Adaptavist(jira_server, jira_username, jira_password)

    # create a test plan
    test_plan_key = atm.create_test_plan(project_key="TEST", test_plan_name="my test plan")

    # create a test cycle (formerly test run) with a set of test cases and add it to test plan
    test_run_key = atm.create_test_run(project_key="TEST", test_run_name="my test cycle", test_cases=["TEST-T1"], test_plan_key=test_plan_key)

    # as test cycle creation also creates/initializes test results, we can just edit these
    atm.edit_test_script_status(test_run_key=test_run_key, test_case_key="TEST-T1", step=1, status="Pass")

    # (optional) edit/overwrite the overall execution status of the test case (by default this is done automatically when editing status of a single step)
    atm.edit_test_result_status(test_run_key=test_run_key, test_case_key="TEST-T1", status="Pass")

   ```

There's much more inside (like adding attachments, creating folders and environments, cloning test cycles). Additional code examples will follow.
