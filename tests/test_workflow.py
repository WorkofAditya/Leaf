from leaf_test_utils import main_wrapper


def run(ctx):
    ctx.repo.mkdir()
    ctx.info("Initializing repository")
    ctx.command(["leaf", "init"])
    ctx.write("test.txt", "one\n")
    ctx.command(["leaf", "add", "."])
    ctx.command(["leaf", "save", "first commit"])
    first = ctx.commit_ids()[-1]
    ctx.write("test.txt", "one\ntwo\n")
    ctx.command(["leaf", "add", "."])
    ctx.command(["leaf", "save", "second commit"])
    second = ctx.commit_ids()[-1]
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


if __name__ == "__main__":
    main_wrapper(__file__, run)
