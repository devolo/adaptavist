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
    folder_name = "/".join((folder_name or "", result.get("name", ""))).replace("//", "/")
    folders.append(folder_name)

    if not result.get("children"):
        return folders

    for child in result["children"]:
        folders.extend(build_folder_names(child, folder_name))

    return folders


def update_list(content: List[Any], new_values: List[Any]) -> List[Any]:
    """Update a list with additional or new values."""
    if new_values[0] == "-":
        return new_values[1:]
    return content + list(set(new_values) - set(content))


def update_multiline_field(content: str, new_values: List[str] = []) -> str:
    """Update a multine custom field (html) with additional or new values."""
    new_content = content[:] if new_values[0] == "-" else ""
    if new_values[0] == "-":
        new_values = new_values[1:]
    return "<br>".join(value for value in new_values if value not in new_content)
