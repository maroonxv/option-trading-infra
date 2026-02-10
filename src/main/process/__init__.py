"""
src/main/process/ - 进程管理模块

包含子进程、父进程和录制进程的实现。

导出:
    - ChildProcess: 工作子进程，负责初始化 VnPy 引擎、加载策略、运行事件循环
    - ParentProcess: 守护父进程，负责监控子进程、自动重启、交易时段调度
    - RecorderProcess: 独立行情录制进程，仅录制行情不运行策略

注意: 使用延迟导入以避免循环依赖和不必要的传递导入。
各进程模块依赖较重（如 ChildProcess 依赖 src.strategy），
因此不在包级别急切导入，而是按需导入。
"""

__all__ = ["ChildProcess", "ParentProcess", "RecorderProcess"]


def __getattr__(name):
    if name == "ChildProcess":
        from src.main.process.child_process import ChildProcess
        return ChildProcess
    if name == "ParentProcess":
        from src.main.process.parent_process import ParentProcess
        return ParentProcess
    if name == "RecorderProcess":
        from src.main.process.recorder_process import RecorderProcess
        return RecorderProcess
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
