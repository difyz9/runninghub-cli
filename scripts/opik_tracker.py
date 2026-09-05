"""
Opik 运行记录跟踪 — 本地文件版
===============================
集成到 runninghub-cli 项目中，自动记录每次生成/提交/下载操作的轨迹。

特性:
- 零依赖（只写JSONL文件）
- 零服务器
- 支持 trace → span 层级
- 支持 metadata 标注
- 可通过 `runninghub opik` CLI 查询

用法:
    from opik_tracker import tracker

    # 自动记录函数
    @tracker.trace(name="文生图生成", project="campus-mv")
    def generate_image(prompt):
        ...

    # 手动记录
    with tracker.trace("提示词优化"):
        tracker.log_input({"scene": "黄昏校园"})
        tracker.log_span("风格选择", {"style": "golden_hour_warm", "score": 100})
        tracker.log_output({"prompt": "..."})

数据存储在: ~/.runninghub/opik_traces/ 下，按日期分文件。
"""

import json
import os
import time
import uuid
import threading
from pathlib import Path
from functools import wraps
from collections import defaultdict
from datetime import datetime
from typing import Optional, Any


# ════════════════════════════════════════════════════════════════
# 配置
# ════════════════════════════════════════════════════════════════

DEFAULT_DIR = Path.home() / ".runninghub" / "opik_traces"
MAX_BATCH = 50  # 每写满50条刷新一次


# ════════════════════════════════════════════════════════════════
# 数据模型
# ════════════════════════════════════════════════════════════════

class Span:
    """一次操作的最小单元"""
    def __init__(self, name: str, trace_id: str, parent_id: Optional[str] = None,
                 metadata: Optional[dict] = None):
        self.span_id = str(uuid.uuid4())[:8]
        self.trace_id = trace_id
        self.parent_id = parent_id
        self.name = name
        self.metadata = metadata or {}
        self.input = {}
        self.output = {}
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "type": "span",
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "metadata": self.metadata,
            "input": self.input,
            "output": self.output,
            "start_time": self.start_time,
            "end_time": self.end_time or time.time(),
            "duration_ms": round((self.end_time or time.time() - self.start_time) * 1000),
            "error": self.error,
        }


class Trace:
    """一组相关操作的整体记录"""
    def __init__(self, name: str, project: str = "default",
                 metadata: Optional[dict] = None):
        self.trace_id = str(uuid.uuid4())[:8]
        self.name = name
        self.project = project
        self.metadata = metadata or {}
        self.input = {}
        self.output = {}
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.spans: list[Span] = []
        self.error: Optional[str] = None

    def add_span(self, span: Span):
        self.spans.append(span)

    def to_dict(self) -> dict:
        return {
            "type": "trace",
            "trace_id": self.trace_id,
            "name": self.name,
            "project": self.project,
            "metadata": self.metadata,
            "input": self.input,
            "output": self.output,
            "start_time": self.start_time,
            "end_time": self.end_time or time.time(),
            "duration_ms": round((self.end_time or time.time() - self.start_time) * 1000),
            "error": self.error,
            "spans": [s.to_dict() for s in self.spans],
            "span_count": len(self.spans),
        }


# ════════════════════════════════════════════════════════════════
# 存储引擎
# ════════════════════════════════════════════════════════════════

class _FileStorage:
    """将 trace 写入 JSONL 文件，按日期分目录"""

    def __init__(self, base_dir: Path = DEFAULT_DIR):
        self.base_dir = base_dir
        self._lock = threading.Lock()
        self._buffer: list[dict] = []

    def _get_file(self) -> Path:
        today = datetime.now().strftime("%Y%m%d")
        file_dir = self.base_dir / today
        file_dir.mkdir(parents=True, exist_ok=True)
        return file_dir / "traces.jsonl"

    def write(self, data: dict):
        with self._lock:
            self._buffer.append(data)
            if len(self._buffer) >= MAX_BATCH:
                self._flush()

    def _flush(self):
        if not self._buffer:
            return
        file_path = self._get_file()
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                for entry in self._buffer:
                    f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            self._buffer.clear()
        except Exception as e:
            print(f"[opik] 写入失败: {e}")

    def search(self, project: str = None, name: str = None,
               limit: int = 20, offset: int = 0) -> list[dict]:
        """搜索最近的 trace"""
        results = []
        # 从最新的文件往前搜
        dates = sorted(self.base_dir.iterdir(), reverse=True)
        for date_dir in dates:
            if not date_dir.is_dir():
                continue
            jsonl_file = date_dir / "traces.jsonl"
            if not jsonl_file.exists():
                continue
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if entry.get("type") != "trace":
                        continue
                    if project and entry.get("project") != project:
                        continue
                    if name and name.lower() not in entry.get("name", "").lower():
                        continue
                    results.append(entry)
        # 按时间倒序
        results.sort(key=lambda x: x.get("start_time", 0), reverse=True)
        return results[offset:offset + limit]

    def get_stats(self) -> dict:
        """统计信息"""
        total_traces = 0
        total_spans = 0
        project_counts = defaultdict(int)
        today = datetime.now().strftime("%Y%m%d")

        for date_dir in self.base_dir.iterdir():
            if not date_dir.is_dir():
                continue
            jsonl_file = date_dir / "traces.jsonl"
            if not jsonl_file.exists():
                continue
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line.strip())
                    if entry.get("type") == "trace":
                        total_traces += 1
                        project_counts[entry.get("project", "default")] += 1
                        total_spans += entry.get("span_count", 0)

        return {
            "total_traces": total_traces,
            "total_spans": total_spans,
            "projects": dict(project_counts),
            "data_dir": str(self.base_dir),
            "today_file": str(self.base_dir / today / "traces.jsonl"),
        }


# ════════════════════════════════════════════════════════════════
# 追踪器（主API）
# ════════════════════════════════════════════════════════════════

class _OpikTracker:
    """
    轻量级本地 Opik 追踪器

    用法:
        from opik_tracker import tracker

        # 方法1: 装饰器
        @tracker.trace(name="文生图")
        def my_func(prompt):
            return result

        # 方法2: 上下文管理器
        with tracker.trace("项目") as t:
            t.log("步骤1")
            t.span("步骤2")
    """

    def __init__(self):
        self._storage = _FileStorage()
        self._current_trace: Optional[Trace] = None
        self._current_span: Optional[Span] = None

    # ── 配置 ──────────────────────────────────────────────

    def configure(self, data_dir: str = None):
        """配置数据存储目录"""
        if data_dir:
            self._storage = _FileStorage(Path(data_dir))

    # ── 装饰器模式 ────────────────────────────────────────

    def trace(self, name: str = None, project: str = "default"):
        """装饰器：自动追踪函数调用"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                trace_name = name or func.__name__
                t = Trace(name=trace_name, project=project)
                self._current_trace = t

                # 记录输入
                sig_params = list(inspect_signature(func).parameters.keys())
                if sig_params:
                    t.input = {k: v for k, v in zip(sig_params, args)}
                    t.input.update(kwargs)

                try:
                    result = func(*args, **kwargs)
                    t.output = {"result": result} if not isinstance(result, dict) else result
                    t.end_time = time.time()
                    self._storage.write(t.to_dict())
                    return result
                except Exception as e:
                    t.error = str(e)
                    t.end_time = time.time()
                    self._storage.write(t.to_dict())
                    raise
                finally:
                    self._current_trace = None
                    self._current_span = None
                    self._flush()
            return wrapper
        return decorator

    # ── 上下文管理器模式 ──────────────────────────────────

    def start_trace(self, name: str, project: str = "default",
                    metadata: dict = None):
        """手动启动一个 trace"""
        self._current_trace = Trace(name=name, project=project, metadata=metadata)
        self._current_span = None
        return self._current_trace

    def end_trace(self, output: dict = None, error: str = None):
        """结束当前 trace"""
        if self._current_trace:
            t = self._current_trace
            if output:
                t.output = output
            if error:
                t.error = error
            t.end_time = time.time()
            self._storage.write(t.to_dict())
            self._flush()
        self._current_trace = None
        self._current_span = None

    def start_span(self, name: str, metadata: dict = None):
        """在当前 trace 下启动一个 span"""
        if not self._current_trace:
            raise RuntimeError("没有活跃的 trace，请先调用 start_trace()")
        parent_id = self._current_span.span_id if self._current_span else None
        span = Span(name=name, trace_id=self._current_trace.trace_id,
                    parent_id=parent_id, metadata=metadata)
        self._current_span = span
        self._current_trace.add_span(span)
        return span

    def end_span(self, output: dict = None, error: str = None):
        """结束当前 span"""
        if self._current_span:
            if output:
                self._current_span.output = output
            if error:
                self._current_span.error = error
            self._current_span.end_time = time.time()
            self._current_span = None  # 回到 trace 层级

    def log_input(self, data: dict):
        """记录当前 trace 的输入"""
        if self._current_span:
            self._current_span.input.update(data)
        elif self._current_trace:
            self._current_trace.input.update(data)

    def log_output(self, data: dict):
        """记录当前 trace 的输出"""
        if self._current_span:
            self._current_span.output.update(data)
        elif self._current_trace:
            self._current_trace.output.update(data)

    def log_metadata(self, key: str, value: Any):
        """添加元数据"""
        target = self._current_span or self._current_trace
        if target:
            target.metadata[key] = value

    # ── 便利方法 ──────────────────────────────────────────

    def log(self, name: str, input_data: dict = None, output_data: dict = None,
            metadata: dict = None):
        """
        快速记录一条 span（自动起止）
        等价于 start_span + log_input + log_output + end_span
        """
        self.start_span(name, metadata=metadata)
        if input_data:
            self.log_input(input_data)
        if output_data:
            self.log_output(output_data)
        self.end_span()

    def span(self, name: str):
        """上下文管理器形式的 span"""
        return _SpanContext(self, name)

    def record_runninghub_task(self, task_id: str, workflow_id: str,
                               prompt: str, style: str = "", score: int = 0,
                               status: str = "SUCCESS"):
        """快速记录一次 RunningHub 任务"""
        with self.span(f"RunningHub任务 {task_id[:8]}"):
            self.log_input({
                "task_id": task_id,
                "workflow_id": workflow_id,
                "prompt_preview": prompt[:100],
                "style": style,
                "quality_score": score,
            })
            self.log_output({
                "status": status,
                "timestamp": datetime.now().isoformat(),
            })

    # ── 查询 ──────────────────────────────────────────────

    def search(self, project: str = None, name: str = None,
               limit: int = 20) -> list[dict]:
        """搜索最近的运行记录"""
        return self._storage.search(project=project, name=name, limit=limit)

    def stats(self) -> dict:
        """统计信息"""
        return self._storage.get_stats()

    # ── 内部 ──────────────────────────────────────────────

    def _flush(self):
        self._storage._flush()


class _SpanContext:
    """上下文管理器：with tracker.span('名称'):"""

    def __init__(self, tracker: _OpikTracker, name: str):
        self.tracker = tracker
        self.name = name

    def __enter__(self):
        self.tracker.start_span(self.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.tracker.end_span(error=str(exc_val))
        else:
            self.tracker.end_span()


# 修复 inspect 签名获取（Python 3.11+ 兼容）
def inspect_signature(func):
    import inspect
    try:
        return inspect.signature(func)
    except (ValueError, TypeError):
        return inspect.Signature()


# ════════════════════════════════════════════════════════════════
# 全局单例
# ════════════════════════════════════════════════════════════════

tracker = _OpikTracker()


# ════════════════════════════════════════════════════════════════
# 快速测试
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== Opik本地追踪器 — 测试 ===")

    # 装饰器模式
    @tracker.trace(name="提示词生成", project="test")
    def gen_prompt(scene: str, style: str = "default"):
        return {"prompt": f"{scene}, cinematic, 8K", "style": style, "score": 98}

    r = gen_prompt("黄昏校园", "golden_hour")
    print(f"  装饰器模式: {r}")

    # 手动模式
    tracker.start_trace("MV制作项目", project="campus_mv", metadata={"scenes": 8})
    tracker.log_input({"scene": "黄昏校园", "workflow": "Z-Image"})
    tracker.log("风格选择", {"scene": "黄昏校园"}, {"style": "golden_hour", "score": 100})
    tracker.log("提交任务", {"task_id": "12345"}, {"status": "SUCCESS"})

    # 在 trace 内包含 RunningHub 任务记录
    tracker.record_runninghub_task(
        task_id="2067496486920474626",
        workflow_id="2037071836214730753",
        prompt="sunset campus basketball...",
        style="golden_hour_warm",
        score=100,
        status="SUCCESS"
    )

    tracker.log_metadata("duration_minutes", 2)
    tracker.end_trace({"prompt": "..."})

    # 查询
    stats = tracker.stats()
    print(f"\n  统计: {stats['total_traces']} traces, {stats['total_spans']} spans")
    print(f"  项目: {stats['projects']}")
    print(f"  数据目录: {stats['data_dir']}")

    traces = tracker.search(project="campus_mv")
    print(f"\n  最近记录: {len(traces)} 条")
    for t in traces[:3]:
        print(f"    [{t['project']}] {t['name']} — {t['duration_ms']}ms ({t['span_count']} spans)")

    print("\n✅ 测试完成")
