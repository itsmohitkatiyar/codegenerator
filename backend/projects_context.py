import os
from typing import List, Optional

# -------------------------------
# Project Context Management
# -------------------------------
current_project: Optional[str] = None  # path to the currently active project
PROJECT_PATH = None
MAX_FILE_SIZE = 10 * 1024  # 10 KB per file
ALLOWED_EXTENSIONS = {".py", ".js", ".json", ".txt",".java"}  # adjust as needed

def set_project(path: str) -> bool:
    """
    Set the current project directory.
    Returns True if successful, False otherwise.
    """
    global current_project
    if os.path.exists(path) and os.path.isdir(path):
        current_project = path
        return True
    return False


def list_project_files(extensions: List[str] = None) -> List[str]:
    """
    List all files in the current project.
    Optionally filter by file extensions.
    """
    if not current_project:
        return []

    if extensions is None:
        extensions = [".py", ".js", ".ts", ".json", ".md"]  # default filter

    files = []
    for root, _, filenames in os.walk(current_project):
        for f in filenames:
            if any(f.endswith(ext) for ext in extensions):
                full_path = os.path.join(root, f)
                files.append(os.path.relpath(full_path, current_project))
    return files


def set_project_path(path: str):
    global PROJECT_PATH
    if os.path.isdir(path):
        PROJECT_PATH = path
    else:
        PROJECT_PATH = None

def get_project_context(project_path=None, max_files=50, max_chars_per_file=2000):
    import os

    if not project_path or not os.path.exists(project_path):
        return ""

    context_lines = []
    file_count = 0

    for root, dirs, files in os.walk(project_path):
        for f in files:
            if file_count >= max_files:
                break
            if f.endswith((".py", ".js", ".ts", ".json", ".md")):
                file_path = os.path.join(root, f)
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read(max_chars_per_file)
                        context_lines.append(
                            f"--- File: {os.path.relpath(file_path, project_path)} ---\n{content}\n"
                        )
                        file_count += 1
                except Exception as e:
                    print(f"Could not read {file_path}: {e}")
        if file_count >= max_files:
            break

    return "\n".join(context_lines) if context_lines else "No readable project files found."
