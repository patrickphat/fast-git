from git import Repo

def get_uncommitted(repo_obj: Repo):
    result_dict = {
        "modified": get_modified(repo_obj),
        "untracked": get_untracked(repo_obj),
    }
    return result_dict

def get_untracked(repo_obj):
    return repo_obj.untracked_files

def get_modified(repo_obj):
    changed_files = [item.a_path for item in repo_obj.index.diff(None)]
    return changed_files