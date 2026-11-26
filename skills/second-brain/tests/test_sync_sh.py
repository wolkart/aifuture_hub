"""sync.sh на временных репозиториях: «голый» репозиторий вместо GitHub, два клона — два устройства."""
import os
import subprocess
import sys
import time

import pytest

from conftest import SCRIPTS, write

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="bash-скрипт — Мак и Linux")
SYNC = SCRIPTS / "sync.sh"
SETUP = ["-c", "user.name=Настройка", "-c", "user.email=setup@test"]


def git(cwd, *args, env=None):
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=True).stdout


@pytest.fixture
def env(tmp_path):
    home, tmp = tmp_path / "home", tmp_path / "tmpdir"
    home.mkdir(); tmp.mkdir()
    notify = tmp_path / "notify.sh"
    notify.write_text('#!/bin/bash\necho "$1|$2" >> "%s"\n' % (tmp_path / "notify.log"), encoding="utf-8")
    notify.chmod(0o755)
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    e.update(HOME=str(home), TMPDIR=str(tmp), GIT_CONFIG_NOSYSTEM="1", SECOND_BRAIN_NOTIFY=str(notify))
    return e


@pytest.fixture
def repos(tmp_path, env):
    """remote.git + клоны «Второй мозг» (A) и b (B) с общим первым коммитом."""
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote), env=env)
    a = tmp_path / "Второй мозг"
    git(tmp_path, "init", "-q", "-b", "main", str(a), env=env)
    write(a, "note.md", "строка\n")
    git(a, "add", "-A", env=env)
    git(a, *SETUP, "commit", "-q", "-m", "init", env=env)
    git(a, "remote", "add", "origin", str(remote), env=env)
    git(a, "push", "-q", "-u", "origin", "main", env=env)
    b = tmp_path / "b"
    git(tmp_path, "clone", "-q", str(remote), str(b), env=env)
    return remote, a, b


def sync(vault, env):
    return subprocess.run(["bash", str(SYNC), str(vault)], env=env, capture_output=True, text=True)


def notifications(tmp_path):
    p = tmp_path / "notify.log"
    return p.read_text(encoding="utf-8").splitlines() if p.exists() else []


def lock_path(vault, env):
    real = subprocess.run(["bash", "-c", 'cd "$1" && pwd -P', "_", str(vault)], capture_output=True, text=True).stdout.strip()
    ck = subprocess.run(["cksum"], input=real, capture_output=True, text=True).stdout.split()[0]
    return os.path.join(env["TMPDIR"], f"second-brain-sync-{ck}.lock")


def test_commit_only_without_origin(tmp_path, env):
    v = tmp_path / "solo"
    git(tmp_path, "init", "-q", "-b", "main", str(v), env=env)
    write(v, "a.md", "текст\n")
    r = sync(v, env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert git(v, "log", "-1", "--format=%s", env=env).startswith("auto: ")
    assert git(v, "log", "-1", "--format=%an", env=env).strip() == "Второй мозг"


def test_own_identity_kept(repos, env):
    _, a, _ = repos
    git(a, "config", "user.name", "Аня", env=env); git(a, "config", "user.email", "a@a", env=env)
    write(a, "x.md", "x\n")
    assert sync(a, env).returncode == 0
    assert git(a, "log", "-1", "--format=%an", env=env).strip() == "Аня"


def test_push(repos, env):
    remote, a, _ = repos
    write(a, "new.md", "новое\n")
    r = sync(a, env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "new.md" in git(remote, "ls-tree", "--name-only", "main", env=env)
    assert r.stdout.strip().endswith("ок")


def test_pull_other_side(repos, env):
    _, a, b = repos
    write(a, "from-a.md", "a\n")
    assert sync(a, env).returncode == 0
    assert sync(b, env).returncode == 0
    assert (b / "from-a.md").exists()


def test_rebase_without_identity(repos, env):
    remote, a, b = repos
    write(a, "a.md", "a\n"); assert sync(a, env).returncode == 0
    write(b, "b.md", "b\n")
    r = sync(b, env)
    assert r.returncode == 0, r.stdout + r.stderr
    names = git(remote, "ls-tree", "--name-only", "main", env=env)
    assert "a.md" in names and "b.md" in names


def test_lock_skip(repos, env):
    _, a, _ = repos
    os.mkdir(lock_path(a, env))
    write(a, "x.md", "x\n")
    r = sync(a, env)
    assert r.returncode == 0 and "пропуск" in r.stdout
    assert "x.md" not in git(a, "ls-tree", "--name-only", "HEAD", env=env)


def test_stale_lock_removed(repos, env):
    _, a, _ = repos
    lock = lock_path(a, env)
    os.mkdir(lock)
    old = time.time() - 20 * 60
    os.utime(lock, (old, old))
    write(a, "x.md", "x\n")
    r = sync(a, env)
    assert r.returncode == 0, r.stdout
    assert "x.md" in git(a, "ls-tree", "--name-only", "HEAD", env=env)
    assert not os.path.exists(lock)


def test_conflict_marks_and_notifies_once(tmp_path, repos, env):
    _, a, b = repos
    write(a, "note.md", "версия A\n"); assert sync(a, env).returncode == 0
    write(b, "note.md", "версия B\n")
    r = sync(b, env)
    assert r.returncode == 1, r.stdout + r.stderr
    assert (b / ".git" / "second-brain-conflict").exists()
    assert not (b / ".git" / "rebase-merge").exists() and not (b / ".git" / "rebase-apply").exists()
    assert (b / "note.md").read_text(encoding="utf-8") == "версия B\n"
    assert len(notifications(tmp_path)) == 1
    write(b, "later.md", "позже\n")
    r2 = sync(b, env)
    assert r2.returncode == 0 and "стоит конфликт" in r2.stdout
    assert "later.md" in git(b, "ls-tree", "--name-only", "HEAD", env=env)
    assert len(notifications(tmp_path)) == 1


def test_offline_is_not_conflict(repos, env):
    _, a, _ = repos
    git(a, "remote", "set-url", "origin", "/нет/такого/репозитория.git", env=env)
    write(a, "x.md", "x\n")
    r = sync(a, env)
    assert r.returncode == 2, r.stdout + r.stderr
    assert not (a / ".git" / "second-brain-conflict").exists()
    assert "x.md" in git(a, "ls-tree", "--name-only", "HEAD", env=env)


def test_space_cyrillic_path(repos, env):
    _, a, _ = repos   # клон A лежит в папке «Второй мозг»
    write(a, "y.md", "y\n")
    assert sync(a, env).returncode == 0


@pytest.mark.skipif(sys.platform != "darwin", reason="launchd — только Мак")
def test_install_sync_plist(repos, env):
    _, a, _ = repos
    r = subprocess.run(["bash", str(SCRIPTS / "install-sync.sh"), str(a), "--no-load"],
                       env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    home = env["HOME"]
    bin_ = os.path.join(home, ".local/bin/second-brain-sync.sh")
    plist = os.path.join(home, "Library/LaunchAgents/local.second-brain.sync.plist")
    assert os.access(bin_, os.X_OK)
    assert subprocess.run(["plutil", "-lint", plist], capture_output=True).returncode == 0
    text = open(plist, encoding="utf-8").read()
    assert str(a) in text and "<integer>300</integer>" in text and bin_ in text


@pytest.mark.skipif(sys.platform != "darwin", reason="launchd — только Мак")
def test_install_sync_custom_label_separate_files(repos, env):
    """Тестовая метка не должна перезаписать скрипт и лог настоящей задачи."""
    _, a, _ = repos
    r = subprocess.run(["bash", str(SCRIPTS / "install-sync.sh"), str(a), "--label", "local.second-brain.sync.test", "--no-load"],
                       env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    home = env["HOME"]
    assert not os.path.exists(os.path.join(home, ".local/bin/second-brain-sync.sh"))
    text = open(os.path.join(home, "Library/LaunchAgents/local.second-brain.sync.test.plist"), encoding="utf-8").read()
    assert os.path.join(home, ".local/bin/local.second-brain.sync.test.sh") in text
    assert os.path.join(home, "Library/Logs/local.second-brain.sync.test.log") in text
