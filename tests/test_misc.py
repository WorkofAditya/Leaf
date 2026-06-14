from leaf_test_utils import main_wrapper


def run(ctx):
    source = ctx.root / "source"
    source.mkdir()
    ctx.repo = source
    ctx.command(["leaf", "init"], cwd=source)
    ctx.write("tracked.txt", "v1\n", cwd=source)
    ctx.command(["leaf", "add", "."], cwd=source)
    ctx.command(["leaf", "save", "initial"], cwd=source)
    first = ctx.commit_ids()[-1]
    ctx.command(["leaf", "tag", "v1", first], cwd=source)
    tags = ctx.command(["leaf", "tag"], cwd=source)
    ctx.check("v1" in tags.stdout and first in tags.stdout, "Tag listing points v1 to first commit")
    ctx.write("tracked.txt", "v2\n", cwd=source)
    ctx.command(["leaf", "add", "."], cwd=source)
    ctx.command(["leaf", "save", "second"], cwd=source)
    second = ctx.commit_ids()[-1]
    ctx.command(["leaf", "tag", "latest"], cwd=source)
    saved_tags = ctx.load_json(".leaf/tags.json", cwd=source)
    ctx.check(saved_tags["v1"] == first and saved_tags["latest"] == second, "Tags file stores expected commits")

    clone_dest = ctx.root / "clone"
    ctx.command(["leaf", "clone", str(source), str(clone_dest)], cwd=ctx.root)
    ctx.check((clone_dest / ".leaf" / "log.json").exists(), "Clone contains Leaf metadata")
    ctx.check((clone_dest / "tracked.txt").read_text(encoding="utf-8") == "v2\n", "Clone preserves working files")
    clone_log = ctx.command(["leaf", "log"], cwd=clone_dest)
    ctx.check("initial" in clone_log.stdout and "second" in clone_log.stdout, "Clone preserves history")

    ctx.command(["leaf", "ignore", "ignored_dir"], cwd=source)
    ctx.write("ignored_dir/ignored.txt", "secret\n", cwd=source)
    status = ctx.command(["leaf", "status"], cwd=source)
    ctx.check("ignored_dir" not in status.stdout and "ignored.txt" not in status.stdout, "Ignored file is not reported by status")
    ctx.command(["leaf", "add", "."], cwd=source)
    ctx.command(["leaf", "save", "ignored check"], cwd=source)
    latest = ctx.load_json(".leaf/log.json", cwd=source)[-1]
    serialized = str(latest)
    ctx.check("ignored.txt" not in serialized, "Ignored file is not tracked in latest commit")

    ctx.command(["leaf", "fsck"], cwd=source, contains="OK")
    ctx.command(["leaf", "help"], cwd=source, contains="Usage")
    ctx.command(["leaf", "version"], cwd=source)


if __name__ == "__main__":
    main_wrapper(__file__, run)
