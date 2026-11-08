"""One-click setup of the original Guangrong 1.1.0 publisher archive.

The game reader DOES NOT distribute or modify third-party binaries. On the
user's explicit request, it downloads the official release, checks the exact
published GitHub asset SHA-256, and installs its synthDrivers subtree into the
user's own %LOCALAPPDATA%\GameTextReader directory.

Offline thereafter; completely separate from BaoYi, NVDA, their config and
their audio channels. The original archive does NOT include optional Microsoft
NaturalVoices; the initial test can only exercise included base voices.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import urllib.request
import zipfile

RELEASE_URL = (
    "https://github.com/shenguangrong/grtts_nvda_plugin/"
    "releases/download/1.1.0/grtts.nvda-addon"
)
# Actual official GitHub release asset digest, verified on Windows CI.
ASSET_SHA256 = "14ba0d4155549a1e4b76335687c960815c87e16f3e34907e1476d206c3609a77"
MAX_ARCHIVE_BYTES = 210 * 1024 * 1024
MAX_EXTRACT_BYTES = 800 * 1024 * 1024


def runtime_directory() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "GameTextReader"
    return base / "GuangrongIndependent"


def installed_x64_dll() -> Path | None:
    file = runtime_directory() / "grtts_x64.dll"
    return file if file.is_file() else None


def _safe_member(info: zipfile.ZipInfo) -> Path | None:
    raw = info.filename.replace("\\", "/")
    p = PurePosixPath(raw)
    if p.is_absolute() or ".." in p.parts or any(":" in part for part in p.parts):
        raise ValueError("官方压缩包包含不安全路径，已中止安装")
    if not p.parts or p.parts[0].lower() != "synthdrivers":
        return None
    if len(p.parts) == 1:
        return None
    # Preserve vendor directory structure; only extract engine resources.
    return Path(*p.parts[1:])


def install_official_guangrong(progress=None) -> str:
    """Installer runs ONLY on a background thread after direct user consent."""
    def say(message: str):
        if progress:
            progress(message)

    target = runtime_directory()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="grtts-setup-", dir=str(target.parent)))
    download = temporary / "original-publisher-grtts.nvda-addon"
    staged = temporary / "runtime"
    staged.mkdir()
    try:
        say("下载广荣 TTS 作者发布的官方原版组件（约 159 MB）...")
        request = urllib.request.Request(
            RELEASE_URL,
            headers={"User-Agent": "GameTextReader-StandaloneTTS-Setup/1.5"}
        )
        digest = hashlib.sha256()
        size = 0
        next_report = 0
        with urllib.request.urlopen(request, timeout=40) as response, download.open("wb") as out:
            while True:
                chunk = response.read(512 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_ARCHIVE_BYTES:
                    raise ValueError("官方组件下载体积异常，已停止")
                digest.update(chunk)
                out.write(chunk)
                if size >= next_report:
                    say(f"正在获取官方组件：{size // (1024 * 1024)} MiB")
                    next_report = size + 8 * 1024 * 1024
        if digest.hexdigest().lower() != ASSET_SHA256:
            raise ValueError("官方资源校验不一致，安装被阻止。"
                             "可能下载中断或作者已重新发布，请重新核查官方版本。")
        say("下载校验通过，正在解压独立语音运行环境...")
        total = 0
        members = 0
        with zipfile.ZipFile(download) as z:
            if z.testzip() is not None:
                raise ValueError("官方资源 ZIP CRC 校验失败")
            for info in z.infolist():
                relative = _safe_member(info)
                if relative is None or info.is_dir():
                    continue
                total += info.file_size
                if total > MAX_EXTRACT_BYTES:
                    raise ValueError("官方资源解压体积异常")
                dest = staged / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info, "r") as source, dest.open("wb") as output:
                    shutil.copyfileobj(source, output, 1024 * 1024)
                members += 1
        dll = staged / "grtts_x64.dll"
        if not dll.is_file() or dll.stat().st_size < 100000:
            raise RuntimeError("官方包缺少 64 位 grtts_x64.dll，未安装")
        if not any(staged.glob("ydvoice*.vl")):
            raise RuntimeError("官方包缺少基础音库，未安装")
        backup = temporary / "previous"
        if target.exists():
            target.rename(backup)
        try:
            staged.rename(target)
        except BaseException:
            if backup.exists():
                backup.rename(target)
            raise
        say(f"官方组件安装完成，{members} 个文件；正在独立检查语音引擎...")
        return str(target / "grtts_x64.dll")
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
