from git.repo.base import Repo
from fgit.utils.git import get_uncommitted
from fgit.utils.message_box import border_msg

def push(repo_path: str, message = "update"):
    ''' 
    Instructional push to an active branch
    '''    
    repo = Repo(repo_path)
    uncommited = get_uncommitted(repo)
    modified, untracked = uncommited["modified"], uncommited["untracked"]
    all_files = modified + untracked
    n_all = len(all_files)
    n_modified = len(modified)
    n_untracked = len(untracked)

    border_msg(f"Active branch: {repo.active_branch}")
    
    # Print uncommited (list by number)
    for i, file in enumerate(all_files):
        # Print header
        if i == 0 and n_modified!=0:
            print("\n● Modified:")
        elif i == n_modified and n_untracked!=0:
            print("\n● Untracked:")
        print(f"[{i}] {file}")
    if n_all != 0:
        committed_ids = [int(i) for i in input("\nCommit ids: ").split()]
    else:
        print("Nothing to commit.")
    commited_files = [file for i, file in enumerate(all_files) if i in committed_ids]
    commit_message = input("Commit message: ")

    repo.index.add(commited_files)
    repo.index.commit(commit_message)
    
    repo.git.push("origin", repo.active_branch)
    print(f"Woohoo!~ Pushed to {repo.remotes.origin.url}| branch: {repo.active_branch}")
