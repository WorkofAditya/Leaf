from leaf_test_utils import main_wrapper


def run(ctx):
    ctx.repo.mkdir()
    ctx.info("Initializing repository")
    ctx.command(["leaf", "init"])
    ctx.command(["leaf", "reset"], contains="Cleared staging area")
    ctx.write("test.txt", "one\n")
    ctx.write("nested/beta.txt", "beta\n")
    ctx.write("folder/deep/file.txt", "directory staging\n")
    ctx.command(["leaf", "add", "folder"], contains="Staged 1 path(s)")
    staged = ctx.load_json(".leaf/index.json")
    ctx.check("folder/deep/file.txt" in staged, "Directory add stages nested files")
    ctx.command(["leaf", "add", "."])
    ctx.command(["leaf", "save", "first commit"])
    first = ctx.commit_ids()[-1]
    ctx.command(["leaf", "save", "no changes"], contains="No changes detected")
    ctx.command(["leaf", "diff", first], contains="No differences found")
    ctx.command(["leaf", "diff", "not-a-commit"], contains="Invalid commit id")
    ctx.command(["leaf", "restore", "not-a-commit"], contains="Invalid commit id")
    ctx.command(["leaf", "revert", "not-a-commit"], contains="Invalid commit id")
    ctx.write("test.txt", "one\ntwo\n")
    ctx.command(["leaf", "add", "."])
    ctx.command(["leaf", "save", "second commit"])
    second = ctx.commit_ids()[-1]
    second_commit_dir = ctx.repo / ".leaf" / "commits" / second
    ctx.check(not (second_commit_dir / "state").exists(), "Diff commit does not duplicate the full repository state")
    ctx.command(["leaf", "status"], contains="Clean working tree")
    ctx.write("test.txt", "one\ntwo\nthree\n")
    ctx.command(["leaf", "diff"], contains="three")
    log = ctx.command(["leaf", "log"])
    ctx.check("first commit" in log.stdout and "second commit" in log.stdout, "Log shows both commits")
    ctx.command(["leaf", "restore", first])
    ctx.assert_file("test.txt", "one\n")
    ctx.command(["leaf", "restore", second])
    ctx.assert_file("test.txt", "one\ntwo\n")
    ctx.write("test.txt", "one\ntwo\nsoft worktree\n")
    ctx.command(["leaf", "reset", "--soft", first])
    ctx.assert_file("test.txt", "one\ntwo\nsoft worktree\n")
    ctx.command(["leaf", "reset", "--hard", second])
    ctx.assert_file("test.txt", "one\ntwo\n")
    ctx.command(["leaf", "revert", second])
    ctx.assert_file("test.txt", "one\n")
    history = ctx.command(["leaf", "log"])
    ctx.check("Revert" in history.stdout and first in history.stdout, "History contains revert and original commit")

    ctx.write("gamma.txt", "gamma\n")
    (ctx.repo / "nested" / "beta.txt").unlink()
    status = ctx.command(["leaf", "status"])
    ctx.check("Added: gamma.txt" in status.stdout, "Status reports added files")
    ctx.check("Deleted: nested/beta.txt" in status.stdout, "Status reports deleted files")
    ctx.command(["leaf", "add", "nested/beta.txt"], contains="Staged 1 path(s)")
    ctx.command(["leaf", "add", "."], contains="Staged")
    ctx.command(["leaf", "reset", "gamma.txt"], contains="Unstaged gamma.txt")
    ctx.command(["leaf", "reset", "gamma.txt"], contains="Nothing staged for gamma.txt")

    ctx.command(["leaf", "save", "remove nested file"], contains="Saved commit")
    deletion_commit = ctx.commits()[-1]
    ctx.check(
        "nested/beta.txt" in deletion_commit.get("deleted", []),
        "Deleted tracked files are recorded in commit metadata",
    )
    ctx.check(
        not (ctx.repo / "nested" / "beta.txt").exists(),
        "Deleted tracked files stay absent after the commit",
    )
    ctx.command(["leaf", "fsck"], contains="Repository integrity OK")


if __name__ == "__main__":
    main_wrapper(__file__, run)
