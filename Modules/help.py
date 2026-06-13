def leaf_help():
    print("""Leaf Version Control System

USAGE:
    leaf <command> [options]
    leaf help
    leaf --help

DESCRIPTION:
    Leaf is a lightweight local version control system for saving snapshots,
    reviewing history, managing branches, merging work, and restoring files.

COMMANDS:
    init
        Create a new Leaf repository in the current directory.

        Usage:
            leaf init

    save <message>
        Save tracked working-tree changes as a new commit. If files were staged
        with `leaf add`, only staged content is saved.

        Usage:
            leaf save "describe your change"

    add <path>
        Stage a file or directory so the next save records only staged changes.

        Usage:
            leaf add <file-or-directory>

    reset [--soft|--hard] [commit]
        Move the current branch to a commit. Use --soft to keep the working tree
        unchanged, or --hard to rewrite the working tree to the target commit.

        Usage:
            leaf reset [commit]
            leaf reset --soft <commit>
            leaf reset --hard <commit>

    reset <path>
        Unstage a file or directory from the index.

        Usage:
            leaf reset <file-or-directory>

    revert <commit_id>
        Apply a new commit that reverses the changes introduced by a commit.

        Usage:
            leaf revert <commit_id>

    log
        Show commit history from HEAD, including messages, timestamps, tags, and
        merge parents.

        Usage:
            leaf log

    restore <commit_id>
        Restore the working tree to a commit and enter detached HEAD state.

        Usage:
            leaf restore <commit_id>

    status
        Show staged files, working-tree changes, deletions, and merge conflicts.

        Usage:
            leaf status

    diff [commit_id]
        Compare the working tree with a commit. Defaults to HEAD when no commit
        is provided.

        Usage:
            leaf diff
            leaf diff <commit_id>

    ignore <path>
        Add a file or directory pattern to Leaf's ignore list.

        Usage:
            leaf ignore <file-or-directory>

    branch [name] [commit]
        List branches, create a branch at HEAD, or create a branch at a specific
        commit.

        Usage:
            leaf branch
            leaf branch <name>
            leaf branch <name> <commit_id>

    checkout <branch>
        Switch to a branch and restore its saved working-tree state.

        Usage:
            leaf checkout <branch>

    merge <branch>|--continue|--abort
        Merge another branch into the current branch, continue after resolving
        conflicts, or abort an in-progress merge.

        Usage:
            leaf merge <branch>
            leaf merge --continue
            leaf merge --abort

    tag [name] [commit]
        List tags, create a tag at HEAD, or create a tag at a specific commit.

        Usage:
            leaf tag
            leaf tag <name>
            leaf tag <name> <commit_id>

    clone <path> [dest]
        Copy an existing local Leaf repository into a new destination directory.

        Usage:
            leaf clone <source-path> [destination]

    fsck
        Check repository integrity, including commit parent, branch, and tag
        references.

        Usage:
            leaf fsck

    version
        Print the latest available Leaf version.

        Usage:
            leaf version
            leaf v
            leaf -v

DISABLED REMOTE COMMANDS:
    Remote synchronization commands are currently disabled. Their code remains
    in the source as comments so it can be reviewed or restored later, but it is
    not executed by the CLI.

    remote [add <name> <path>]
        Disabled. Previously listed or added local repository remotes.

    fetch <remote>
        Disabled. Previously copied commits and remote branch references from a
        configured remote.

    pull <remote> <branch>
        Disabled. Previously fetched a remote branch and merged it locally.

    push <remote> <branch>
        Disabled. Previously copied local commits and a branch pointer to a
        configured remote.
""")
