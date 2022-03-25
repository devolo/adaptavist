# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.1] - 2022/03/25

### Fixed

- Toggling build_url and code_base

## [2.2.0] - 2022/01/10

## Added

- Ability to create test runs with given application version

## [2.1.0] - 2021/11/17

### Added

- Mark package as typed
- Methods to get attachments

### Changed

- Test steps in test results are now sorted by index

### Fixed

- Fixed uppercase-lowercase in constants
- If a test case is created without dedicated status, it is set to "Not Executed" now

## [2.0.0] - 2021/05/31

### Added

- Ability to create test runs with given executor or assignee
- Ability to create test cases in different statuses

### Changed

- *BREAKING*: If the docs say list, they mean list. Strings are not supported anymore.
- *BREAKING*: To move test cases to the root folder, "/" is needed
- *BREAKING*: Uploading attachments now works via test run and test case key

## [1.1.2] - 2020/11/14

### Added

- Resolved package requirements

## [1.1.1] - 2020/10/08

### Fixed

- Editing of test case custom fields

## [1.1.0] - 2020/03/03

### Added

- Added methods to create and delete test cases and added support to set/change objective and labels of test plans and to change name, objective, etc. of test cases

### Changed

- Set assignee to executor by default

## [1.0.0] - 2020/03/04

### Added

- Python package providing functionality for Jira Test Management.
