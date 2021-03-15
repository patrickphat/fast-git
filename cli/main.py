import argparse 
from fgit.actions import push

def main():
    parser = argparse.ArgumentParser(prog ='fgit', description ='FastGit commandline interface') 
    parser.add_argument("action", type=str, help = "action to perform: push.")
    parser.add_argument("-m","--message", type=str, help = "commit message")

    args = parser.parse_args() 
    action = args.action

    if action == "push":
        push("." , message = args.message)