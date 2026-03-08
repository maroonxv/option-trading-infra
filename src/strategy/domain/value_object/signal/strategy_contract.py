"""策略契约值对象。

定义策略作者与基础设施之间的明确契约：
- 指标阶段上下文与输出
- 信号阶段上下文与输出
- 期权选择偏好
- 决策流水线阶段记录与轨迹
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4


@dataclass(frozen=True)
class OptionSelectionPreference:
    """信号阶段输出的期权选择偏好。"""

    option_type: Optional[str] = None
    strike_level: Optional[int] = None
    target_delta: Optional[float] = None
    combination_type: Optional[str] = None
    side: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IndicatorContext:
    """指标计算契约上下文。"""

    vt_symbol: str
    timestamp: datetime
    bar: Dict[str, Any]
    underlying_price: float
    option_chain: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IndicatorComputationResult:
    """指标计算输出。"""

    indicator_key: str = "noop"
    updated_indicator_keys: List[str] = field(default_factory=list)
    values: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def noop(cls, summary: str = "未启用指标计算") -> "IndicatorComputationResult":
        return cls(summary=summary)


@dataclass(frozen=True)
class SignalContext:
    """信号判断契约上下文。"""

    vt_symbol: str
    timestamp: datetime
    underlying_price: float
    option_chain: Any = None
    indicator_result: Optional[IndicatorComputationResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SignalDecision:
    """信号阶段输出。"""

    action: str
    signal_name: str
    rationale: str = ""
    confidence: float = 0.0
    selection_preference: Optional[OptionSelectionPreference] = None
    close_target_symbol: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_open(self) -> bool:
        return self.action == "open"

    @property
    def is_close(self) -> bool:
        return self.action == "close"


@dataclass(frozen=True)
class PipelineStageRecord:
    """决策流水线阶段记录。"""

    stage: str
    status: str
    summary: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionTrace:
    """一条 bar/持仓决策的完整轨迹。"""

    vt_symbol: str
    bar_dt: datetime
    trace_type: str
    signal_name: str = ""
    trace_id: str = field(default_factory=lambda: uuid4().hex)
    stages: List[PipelineStageRecord] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def append_stage(
        self,
        stage: str,
        status: str,
        summary: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.stages.append(
            PipelineStageRecord(
                stage=stage,
                status=status,
                summary=summary,
                payload=dict(payload or {}),
            )
        )

    def to_payload(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "vt_symbol": self.vt_symbol,
            "bar_dt": self.bar_dt,
            "trace_type": self.trace_type,
            "signal_name": self.signal_name,
            "stages": [
                {
                    "stage": item.stage,
                    "status": item.status,
                    "summary": item.summary,
                    "payload": item.payload,
                }
                for item in self.stages
            ],
            "metadata": dict(self.metadata),
        }
