# path: tests/test_signal.py

import asyncio
import signal
import pytest

from f2.utils._signal import SignalManager


def test_handle_signal_without_running_loop_still_exits():
    """
    信号在解释器关闭期间到达时（threading._shutdown() 中已无事件循环），
    _handle_signal 必须仍然走到 finally 并调用 sys.exit()。

    回归测试：get_running_loop() 曾经写在 try 外面，抛出
    "RuntimeError: no running event loop" 后 finally 不再执行，
    systemd 只能看到 status=1/FAILURE，数据库连接也来不及关闭。
    """
    manager = SignalManager()
    manager.shutdown_event.clear()

    try:
        # 此处没有运行中的事件循环 —— 正是崩溃时的场景
        with pytest.raises(RuntimeError):
            asyncio.get_running_loop()

        with pytest.raises(SystemExit):
            manager._handle_signal(signal.SIGTERM, None)

        # 即使没有事件循环，关闭事件也必须被设置
        assert manager.shutdown_event.is_set()
    finally:
        # SignalManager 是单例，必须还原状态，否则会污染其它测试
        manager.shutdown_event.clear()


# 模拟长时间运行的任务
@pytest.mark.asyncio
async def test_long_running_task_without_shutdown():
    """
    测试长时间运行的任务，未触发 shutdown 信号
    """
    task = asyncio.create_task(long_running_task())

    # 等待任务完成
    await task
    # 确保任务完成
    assert task.done()


# 模拟长时间运行的任务，触发 shutdown
@pytest.mark.asyncio
async def test_long_running_task_with_shutdown():
    """
    测试长时间运行的任务，触发 shutdown 信号
    """
    # 创建 SignalManager 实例并注册信号
    signal_manager = SignalManager()
    signal_manager.register_shutdown_signal()

    # 创建并启动任务
    task = asyncio.create_task(long_running_task())

    # 等待任务开始运行
    await asyncio.sleep(0.1)

    # 模拟接收到 SIGINT 信号，触发 shutdown 逻辑
    signal_manager._shutdown_event.set()

    # 明确调用取消任务
    task.cancel()

    # 等待任务结束
    await asyncio.sleep(0.2)
    # 确保任务完成
    assert task.done()
    # 确保任务被取消
    assert task.cancelled()


# 模拟的长时间运行任务
@pytest.mark.asyncio
async def long_running_task():
    print("Start long running task...")
    for i in range(10):
        if SignalManager.is_shutdown_signaled():
            print("Stopping task early due to shutdown signal.")
            break
        print(f"Task is running... ({i+1}/10)")
        await asyncio.sleep(0.1)
    print("End of long running task.")


@pytest.mark.asyncio
async def test_signal_manager_shutdown_event():
    """
    测试 SignalManager 的 shutdown_event 是否在接收到信号后被设置
    """
    signal_manager = SignalManager()

    # 确保 shutdown_event 是清除状态
    signal_manager.shutdown_event.clear()

    # 确认事件开始时未被设置
    assert not signal_manager.shutdown_event.is_set()
