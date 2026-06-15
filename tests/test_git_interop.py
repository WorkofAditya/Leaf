from __future__ import annotations

import shutil

from leaf_test_utils import TestContext, main_wrapper


def run(ctx: TestContext) -> None:
    if shutil.which("git") is None:
        ctx.info("git unavailable; skipping git interoperability test")
        return
    ctx.repo.mkdir(parents=True)
    ctx.command(["git", "init", "-b", "main"])
    ctx.command(["git", "config", "user.name", "Leaf Test"])
    ctx.command(["git", "config", "user.email", "leaf-test@example.invalid"])
    ctx.write("alpha.txt", "one\n")
    ctx.command(["git", "add", "alpha.txt"])
    ctx.command(["git", "commit", "-m", "initial import"])
    ctx.command(["git", "checkout", "-b", "feature"])
    ctx.write("feature.txt", "feature\n")
    ctx.command(["git", "add", "feature.txt"])
    ctx.command(["git", "commit", "-m", "feature work"])
    ctx.command(["git", "checkout", "main"])
    ctx.write("main.txt", "main\n")
    ctx.command(["git", "add", "main.txt"])
    ctx.command(["git", "commit", "-m", "main work"])
    ctx.command(["git", "merge", "feature", "-m", "merge feature"])

    original = ctx.command(["git", "log", "--all", "--format=%s"]).stdout.splitlines()
    ctx.command(["leaf", "import-git"], contains="Imported Git repository")
    ctx.check((ctx.repo / ".git").is_dir(), "import leaves original .git directory untouched")
    ctx.check((ctx.repo / ".leaf" / "log.json").is_file(), "import creates Leaf log")
    log = ctx.commits()
    ctx.check(len(log) == 4, "import recreates all commits")
    ctx.check(any(c["message"] == "merge feature" and len(c.get("parents", [])) == 2 for c in log), "import preserves merge parents")
    branches = ctx.load_json(".leaf/branches.json")
    ctx.check(set(branches) == {"main", "feature"}, "import preserves Git branches")
    ctx.check(ctx.read(".leaf/CURRENT_BRANCH") == "main", "import preserves current branch")

    shutil.rmtree(ctx.repo / ".git")
    ctx.command(["leaf", "export-git"], contains="Exported Leaf repository")
    ctx.check((ctx.repo / ".git").is_dir(), "export creates .git directory")
    exported = ctx.command(["git", "log", "--all", "--format=%s"]).stdout.splitlines()
    ctx.check(exported == original, "export preserves commit messages and history traversal")
    ctx.check(ctx.command(["git", "branch", "--show-current"]).stdout.strip() == "main", "export preserves current branch")
    ctx.check(set(ctx.command(["git", "branch", "--format=%(refname:short)"]).stdout.split()) == {"main", "feature"}, "export preserves branches")
    ctx.assert_file("alpha.txt", "one\n")
    ctx.assert_file("feature.txt", "feature\n")
    ctx.assert_file("main.txt", "main\n")


if __name__ == "__main__":
    main_wrapper(__file__, run)
