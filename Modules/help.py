def leaf_help():
    print("""
Leaf Version Control System

Usage:
  leaf <command> [options]

Commands:

  Repository
    init                 Create a new repository
    clone <path> [dest]  Clone a local repository
    import-git           Import an existing .git repository into .leaf
    export-git           Export an existing .leaf repository into .git
    fsck                 Verify repository integrity

  Changes
    add <path>           Stage files or directories
    save <message>       Create a commit
    status               Show working tree status
    diff [commit]        Show differences
    ignore <path>        Ignore files or directories

  History
    log                  Show commit history
    restore <commit>     Restore a commit
    revert <commit>      Revert a commit
    reset [options]      Move HEAD or unstage files

  Branching
    branch [name]        List or create branches
    checkout <branch>    Switch branches
    merge <branch>       Merge branches

  Tags
    tag [name]           List or create tags

  Information
    version              Show Leaf version
    help                 Show this help

Reset Options:
  leaf reset <path>
      Unstage a file or directory

  leaf reset <commit>
      Move HEAD to a commit

  leaf reset --soft <commit>
      Keep working tree unchanged

  leaf reset --hard <commit>
      Restore files from target commit

Merge Options:
  leaf merge <branch>
      Merge a branch

  leaf merge --continue
      Continue after resolving conflicts

  leaf merge --abort
      Cancel current merge

Aliases:
  leaf help
  leaf --help

  leaf version
  leaf v
  leaf -v

Remote Commands:
  remote    Disabled
  fetch     Disabled
  pull      Disabled
  push      Disabled

""")
