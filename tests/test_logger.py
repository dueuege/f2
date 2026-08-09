# path: tests/test_logger.py

import pytest
import logging
from pathlib import Path
from unittest.mock import patch
from f2.log.logger import LogManager

LOG_DIR = Path("./test_logs")


@pytest.fixture(scope="function")
def log_manager():
    # 创建临时的日志目录
    LOG_DIR.mkdir(exist_ok=True)

    # 初始化日志管理器
    manager = LogManager()
    manager.setup_logging(level=logging.DEBUG, log_to_console=False, log_path=LOG_DIR)

    # 记录一些测试日志
    logger = manager.logger
    logger.debug("Test debug message")
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")

    yield manager, LOG_DIR

    # 清理操作
    manager.shutdown()
    for log_file in LOG_DIR.iterdir():
        log_file.unlink()
    LOG_DIR.rmdir()


def test_log_file_creation(log_manager):
    _, temp_log_dir = log_manager
    # 测试是否已经在指定的目录中创建了日志文件
    log_files = list(temp_log_dir.glob("*.log"))
    assert len(log_files) == 1


def test_clean_logs(log_manager):
    manager, temp_log_dir = log_manager
    # 写入一些测试日志文件
    for _ in range(10):
        manager.logger.debug("debug message")
        manager.logger.info("info message")
    # 清理所有日志
    manager.clean_logs(keep_last_n=3)
    log_files = list(temp_log_dir.glob("*.log"))
    assert len(log_files) == 1


def test_clean_logs_keeps_newest_by_mtime_not_by_name(log_manager):
    """
    回归测试：clean_logs 必须按修改时间保留最近的日志，而不是按文件名。

    按文件名排序时 "f2-trace-*" 永远排在 "f2-<日期>-*" 之后，保留名额会被
    trace 日志占满，于是每次 f2 启动都会删光真正的主日志。NAS 上的 logs/
    曾经因此只剩下一堆 0 字节的 trace 日志，主日志一个都不剩。
    """
    manager, temp_log_dir = log_manager

    # 主日志最新，trace 日志最旧；但按文件名排序时 trace 排在后面。
    old_trace = temp_log_dir / "f2-trace-2026-01-01.log"
    new_main = temp_log_dir / "f2-2026-01-02.log"
    old_trace.write_text("old trace", encoding="utf-8")
    new_main.write_text("new main", encoding="utf-8")

    import os

    os.utime(old_trace, (1_000_000, 1_000_000))
    os.utime(new_main, (2_000_000, 2_000_000))

    # 只保留 1 个：必须是时间最新的主日志，而不是名字最靠后的 trace 日志。
    with patch.object(Path, "glob", lambda self, pattern: [new_main, old_trace]):
        manager.clean_logs(keep_last_n=1)

    assert new_main.exists(), "最新的主日志被误删（按文件名排序的旧行为）"
    assert not old_trace.exists(), "更旧的 trace 日志应当被清理"


def test_clean_logs_survives_vanished_file(log_manager):
    """
    回归测试：多个 f2 进程可能同时清理同一个日志目录（hourly 与 24h 定时任务
    共享 NAS 上的 logs/）。文件在 glob 之后、unlink 之前被另一个进程删除时，
    clean_logs 必须安静跳过。

    该异常原本发生在模块导入阶段（logger.py 顶层调用 log_setup），
    会让 f2 在任何输出之前就崩溃，日志文件因此为 0 字节。
    """
    manager, temp_log_dir = log_manager

    real_log = temp_log_dir / "f2-real.log"
    real_log.write_text("x", encoding="utf-8")
    ghost = temp_log_dir / "f2-deleted-by-another-process.log"
    assert not ghost.exists()

    with patch.object(Path, "glob", lambda self, pattern: [ghost, real_log]):
        manager.clean_logs(keep_last_n=0)  # 不得抛出 FileNotFoundError

    # 真实存在的文件仍然要被清理掉
    assert not real_log.exists()
