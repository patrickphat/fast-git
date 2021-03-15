from git.repo.base import Repo
import numpy as np
from fgit.utils.git import get_uncommitted, get_deleted_files
from fgit.utils.message_box import border_msg

def push(repo_path: str, message = "update"):
    ''' 
    Instructional push to an active branch
    '''    
    repo = Repo(repo_path)
    uncommited = get_uncommitted(repo)
    modified, untracked = uncommited["modified"], uncommited["untracked"]

    deleted, modified = get_deleted_files(modified)
    all_files = modified + deleted + untracked
    n_all = len(all_files)
    # Type cumulative sum
    n_modified = len(modified)
    n_deleted = len(deleted)
    n_untracked = len(untracked)
    t_csum = np.cumsum([n_modified, n_deleted, n_untracked])
    
    border_msg(f"Active branch: {repo.active_branch}")
    
    # Print uncommited (list by number)
    for i, file in enumerate(all_files):
        # Print header
        if i == 0 and (n_modified + n_deleted!=0):
            print("\n● Modified:")
        elif (i == n_modified + n_deleted) and n_untracked!=0:
            print("\n● Untracked:")
        print(f"[{i}] {file}", end = "")
        if t_csum[0] <= i < t_csum[1]:
            print(" - deleted")
        else:
            print("")
    if n_all != 0:
        committed_ids = [int(i) for i in input("\nCommit ids: ").split()]
    else:
        print("Nothing to commit.")
    
    committed_files = []
    committed_del_files = []


    for i, file in enumerate(all_files):
        if i in committed_ids:
           
            if t_csum[1] <= i < t_csum[2]:
                committed_del_files.append(file)
            else:
                committed_files.append(file)

    commit_message = input("Commit message: ")

    repo.git.add(committed_files, update=True)
    repo.index.add(committed_del_files)
    repo.index.commit(commit_message)
    
    repo.git.push("origin", repo.active_branch)
    print(f"Woohoo!~ Pushed to {repo.remotes.origin.url}| branch: {repo.active_branch}")
