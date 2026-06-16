import contextlib
import io
import sys

from leaf_test_utils import main_wrapper


class _FakeVersionResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return b"9.9.9-test\n"


def _fake_urlopen(url, timeout=5):
    return _FakeVersionResponse()


def run(ctx):
    empty = ctx.root / "empty"
    empty.mkdir()
    ctx.repo = empty
    ctx.command(["leaf", "status"], contains="No repository", cwd=empty)
    ctx.command(["leaf", "save", "pre-init"], contains="Not a repository", cwd=empty)
    ctx.command(["leaf", "add", ""], contains="Missing path", cwd=empty)
    ctx.command(["leaf", "diff"], contains="No commits", cwd=empty)
    ctx.command(["leaf", "log"], contains="No commits", cwd=empty)
    ctx.command(["leaf", "restore"], contains="Missing commit id", cwd=empty)
    ctx.command(["leaf", "revert"], contains="Missing commit id", cwd=empty)
    ctx.command(["leaf", "ignore"], contains="Missing file/folder name", cwd=empty)
    ctx.command(["leaf", "checkout"], contains="Missing branch name", cwd=empty)
    ctx.command(["leaf", "merge"], contains="Missing branch name to merge", cwd=empty)
    ctx.command(["leaf", "clone"], contains="Missing source path", cwd=empty)

    source = ctx.root / "source"
    source.mkdir()
    ctx.repo = source
    ctx.command(["leaf", "init"], cwd=source)
    ctx.command(["leaf", "merge", "--continue"], cwd=source, contains="No merge in progress")
    ctx.command(["leaf", "merge", "--abort"], cwd=source, contains="No merge in progress")
    ctx.command(["leaf", "remote"], cwd=source, contains="Remote repository commands are currently disabled")
    ctx.command(["leaf", "fetch", "origin"], cwd=source, contains="Remote repository commands are currently disabled")
    ctx.command(["leaf", "pull", "origin", "main"], cwd=source, contains="Remote repository commands are currently disabled")
    ctx.command(["leaf", "push", "origin", "main"], cwd=source, contains="Remote repository commands are currently disabled")
    ctx.write("tracked.txt", "v1\n", cwd=source)
    ctx.command(["leaf", "add", "."], cwd=source)
    ctx.command(["leaf", "save", "initial"], cwd=source)
    first = ctx.commit_ids()[-1]
    ctx.command(["leaf", "tag", "bad", "not-a-commit"], cwd=source, contains="Invalid commit id")
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

    ctx.command(["leaf", "clone", str(ctx.root / "missing")], cwd=ctx.root, contains="Source is not a Leaf repository")
    clone_dest = ctx.root / "clone"
    ctx.command(["leaf", "clone", str(source), str(clone_dest)], cwd=ctx.root)
    ctx.check((clone_dest / ".leaf" / "log.json").exists(), "Clone contains Leaf metadata")
    ctx.check((clone_dest / "tracked.txt").read_text(encoding="utf-8") == "v2\n", "Clone preserves working files")
    clone_log = ctx.command(["leaf", "log"], cwd=clone_dest)
    ctx.check("initial" in clone_log.stdout and "second" in clone_log.stdout, "Clone preserves history")

    ctx.command(["leaf", "ignore", "ignored_dir"], cwd=source)
    ctx.command(["leaf", "ignore", "deep_ignore"], cwd=source)
    ctx.write("ignored_dir/ignored.txt", "secret\n", cwd=source)
    ctx.write("deep/nested/deep_ignore/ignored.txt", "deep secret\n", cwd=source)
    ctx.write("deep/nested/kept.txt", "keep me\n", cwd=source)
    status = ctx.command(["leaf", "status"], cwd=source)
    ctx.check("ignored_dir" not in status.stdout and "ignored.txt" not in status.stdout, "Ignored file is not reported by status")
    ctx.check("deep_ignore" not in status.stdout and "kept.txt" in status.stdout, "Deep ignored folders are skipped while nearby files are visible")
    (source / "asset.bin").write_bytes(b"leaf\0binary")
    ctx.command(["leaf", "add", "."], cwd=source)
    staged = ctx.load_json(".leaf/index.json", cwd=source)
    ctx.check("asset.bin" not in staged, "Binary file is not staged as text content")
    ctx.command(["leaf", "save", "ignored check"], cwd=source)
    latest = ctx.load_json(".leaf/log.json", cwd=source)[-1]
    serialized = str(latest)
    ctx.check("ignored.txt" not in serialized, "Ignored file is not tracked in latest commit")

    original_log_json = (source / ".leaf" / "log.json").read_text(encoding="utf-8")
    (source / ".leaf" / "log.json").write_text("{not valid json", encoding="utf-8")
    recovered_log = ctx.command(["leaf", "log"], cwd=source)
    ctx.check("initial" in recovered_log.stdout or "second" in recovered_log.stdout, "Corrupted log falls back to backup history")
    (source / ".leaf" / "log.json").write_text(original_log_json, encoding="utf-8")

    sys.path.insert(0, str(ctx.script_path.parents[1]))
    from Modules import commands

    original_urlopen = commands.urllib.request.urlopen
    commands.urllib.request.urlopen = _fake_urlopen
    try:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            commands.leaf_version()
        ctx.check(buffer.getvalue().strip() == "9.9.9-test", "Version command handles successful network response")
    finally:
        commands.urllib.request.urlopen = original_urlopen

    ctx.command(["leaf", "fsck"], cwd=source, contains="OK")
    ctx.command(["leaf", "help"], cwd=source, contains="Usage")
    ctx.command(["leaf", "version"], cwd=source)


if __name__ == "__main__":
    main_wrapper(__file__, run)
