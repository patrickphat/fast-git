import argparse 
import requests
from git.repo.base import Repo
from shutil import copyfile
from .utils.configuration import create_config_from_template
from .utils.git import get_uncommitted
from pathlib import Path


CURRENT_PATH = DEFAULT_CONFIG_PATH = Path(__file__).parent

def main():
    parser = argparse.ArgumentParser(prog ='fgit', description ='FuckGit commandline interface') 
    parser.add_argument("action", type=str, help = "action to perform: push.")
    parser.add_argument("-m","--message", type=str, help = "commit message")

    args = parser.parse_args() 
    action = args.action

    if action == "push":
        push("." , message = args.message)

def push(repo_path, message = "update"):
    ''' 
    Create experiment from a known repository
    '''    
    repo = Repo(repo_path)
    uncommited = get_uncommitted(repo)
    modified, untracked = uncommited["modified"], uncommited["untracked"]
    all_files = modified + untracked
    n_all = len(all_files)
    n_modified = len(modified)
    n_untracked = len(untracked)

    # Print uncommited (list by number)
    for i, file in enumerate(all_files):
        # Print header
        if i == 0:
            print("Modified:")
        elif i == n_modified:
            print("\nUntracked:")
        print(f"[{i}] {file}")

    committed_ids = [int(i) for i in input("\nCommit ids: ").split()]
    commited_files = [file for i, file in enumerate(all_files) if i in committed_ids]
    commit_message = input("Commit message: ")

    repo.index.add(commited_files)
    repo.index.commit(commit_message)
    
    # Push to origin
    repo.remotes.origin.push()
    print(f"Woohoo!~ Pushed to {repo.remotes.origin.url}| branch: {repo.active_branch}")



    


