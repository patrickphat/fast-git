from git import Repo
from typing import List
import os 

def get_uncommitted(repo_obj: Repo):
    result_dict = {
        "modified": get_modified(repo_obj),
        "untracked": get_untracked(repo_obj),
    }
    return result_dict

def get_untracked(repo_obj: Repo):
    return repo_obj.untracked_files

def get_modified(repo_obj: Repo):
    changed_files = [item.a_path for item in repo_obj.index.diff(None)]
    return changed_files

def get_deleted_files(list_paths: List[str]):
    del_files = []
    non_del_files = []
    for path in list_paths:
        if os.path.exists(path):
            non_del_files.append(path)
        else:
            del_files.append(path)
    return del_files, non_del_files