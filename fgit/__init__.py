from .utils import get_uncommitted

def commit(repo_path):

    uncommited = get_uncommitted(repo_path)
    modified, untracked = uncommited["modified"], uncommited["untracked"]  
    all_files = modified + untracked
    num_files = len(all_files)
    num_modified = len(modified)
    num_untracked = len(untracked)

    for i in range(num_files):

    
        
