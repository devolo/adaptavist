"""Helper methods used by the module."""

import getpass
import os
from typing import Any, Dict, List


def get_executor() -> str:
    """Get executor name."""
    build_url = os.environ.get("BUILD_URL")
    jenkins_url = os.environ.get("JENKINS_URL")
    is_jenkins = build_url and jenkins_url and build_url.startswith(jenkins_url)
    return "jenkins" if is_jenkins else getpass.getuser().lower()


def build_folder_names(result: Dict[str, Any], folder_name: str = "") -> List[Any]:
    """Build list of folder names from a hierarchical dictionary."""
    folders = []
    folder_name = "/".join((folder_name, result.get("name", ""))).replace("//", "/")
    folders.append(folder_name)

    if not result.get("children"):
        return folders

    for child in result["children"]:
        folders.extend(build_folder_names(child, folder_name))

    return folders


def raise_on_kwargs_not_empty(kwargs):
    """Raise if there are more keyword arguments than understood."""
    if kwargs:
        raise SyntaxWarning(f"Unknown arguments: {kwargs}")


def update_field(current_values: List[Any], request_data: Dict[str, Any], key: str, new_values: List[Any]) -> None:
    """Append list entries to an existing list and add it to a dictionary, if the new list is different."""
    if new_values and new_values[0] == "-" and current_values != new_values[1:]:
        request_data.update({key: new_values[1:]})
        return

    combined_values = current_values + list(set(new_values) - set(current_values))
    if current_values != combined_values:
        request_data.update({key: combined_values})


def update_multiline_field(current_content: str, request_data: Dict[str, Any], key: str, new_values: List[str]) -> None:
    """Update a multiline custom field (html) with additional or new values."""
    new_content = "" if new_values and new_values[0] == "-" else current_content
    if new_values and new_values[0] == "-":
        new_values = new_values[1:]
    combined_values = "<br>".join(value for value in new_values if value not in new_content)
    if current_content != combined_values:
        request_data.setdefault("customFields", {})[key] = combined_values
