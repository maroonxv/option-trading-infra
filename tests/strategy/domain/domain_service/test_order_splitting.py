"""
订单拆分算法属性测试

Feature: order-splitting-algorithms
"""
import math
from datetime import datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.strategy.domain.domain_service.advanced_order_scheduler import AdvancedOrderScheduler
from src.strategy.domain.value_object.order_instruction import OrderInstruction, Direction, Offset


def make_instruction(volume: int) -> OrderInstruction:
    return OrderInstruction(
        vt_symbol="rb2501.SHFE",
        direction=Direction.LONG,
        offset=Offset.OPEN,
        volume=volume,
        price=4000.0,
    )


class TestTimedSplitProperty:
    """Feature: order-splitting-algorithms, Property 1: 定时拆单拆分正确性"""

    @given(
        total_volume=st.integers(min_value=1, max_value=10000),
        per_order_volume=st.integers(min_value=1, max_value=1000),
        interval_seconds=st.integers(min_value=1, max_value=3600),
    )
    @settings(max_examples=100)
    def test_property1_timed_split_correctness(self, total_volume, per_order_volume, interval_seconds):
        """
        **Validates: Requirements 1.1, 1.2**

        For any valid total_volume and per_order_volume:
        - 每笔子单 volume <= per_order_volume
        - 所有子单 volume 之和 == total_volume
        - 子单数量 == ceil(total_volume / per_order_volume)
        - 第 i 笔子单的 scheduled_time == start_time + i * interval_seconds
        """
        scheduler = AdvancedOrderScheduler()
        instruction = make_instruction(total_volume)
        start_time = datetime(2025, 1, 1, 10, 0, 0)

        order = scheduler.submit_timed_split(instruction, interval_seconds, per_order_volume, start_time)

        # 每笔子单 volume <= per_order_volume
        for child in order.child_orders:
            assert child.volume <= per_order_volume

        # 所有子单 volume 之和 == total_volume
        assert sum(c.volume for c in order.child_orders) == total_volume

        # 子单数量 == ceil(total_volume / per_order_volume)
        expected_count = math.ceil(total_volume / per_order_volume)
        assert len(order.child_orders) == expected_count

        # 第 i 笔子单的 scheduled_time == start_time + i * interval_seconds
        for i, child in enumerate(order.child_orders):
            expected_time = start_time + timedelta(seconds=interval_seconds * i)
            assert child.scheduled_time == expected_time


class TestEnhancedTWAPProperty:
    """Feature: order-splitting-algorithms, Property 6: 增强型 TWAP 拆分正确性"""

    @given(
        total_volume=st.integers(min_value=1, max_value=10000),
        time_window_seconds=st.integers(min_value=1, max_value=86400),
        num_slices=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    def test_property6_enhanced_twap_correctness(self, total_volume, time_window_seconds, num_slices):
        """
        **Validates: Requirements 3.1, 3.2**

        For any valid total_volume, time_window_seconds and num_slices:
        - 各片数量差异不超过 1（max - min ≤ 1）
        - 所有子单 volume 之和 == total_volume
        - 相邻时间片间隔 == time_window_seconds / num_slices（±1 秒舍入误差）
        """
        scheduler = AdvancedOrderScheduler()
        instruction = make_instruction(total_volume)
        start_time = datetime(2025, 1, 1, 10, 0, 0)

        order = scheduler.submit_enhanced_twap(instruction, time_window_seconds, num_slices, start_time)

        children = order.child_orders
        assert len(children) == num_slices

        volumes = [c.volume for c in children]

        # 各片数量差异不超过 1（max - min ≤ 1）
        assert max(volumes) - min(volumes) <= 1

        # 所有子单 volume 之和 == total_volume
        assert sum(volumes) == total_volume

        # 相邻时间片间隔 == time_window_seconds / num_slices（±1 秒舍入误差）
        expected_interval = time_window_seconds / num_slices
        for i in range(1, len(children)):
            actual_interval = (children[i].scheduled_time - children[i - 1].scheduled_time).total_seconds()
            assert abs(actual_interval - expected_interval) <= 1.0, (
                f"Slice {i}: actual_interval={actual_interval}, expected={expected_interval}"
            )

# --- Strategies for Property 7 ---

@st.composite
def order_type_strategy(draw):
    """随机选择一种新订单类型并生成对应的有效参数和订单"""
    order_type = draw(st.sampled_from(["timed_split", "classic_iceberg", "enhanced_twap"]))
    total_volume = draw(st.integers(min_value=1, max_value=500))
    instruction = make_instruction(total_volume)
    scheduler = AdvancedOrderScheduler()
    start_time = datetime(2025, 1, 1, 10, 0, 0)

    if order_type == "timed_split":
        per_order_volume = draw(st.integers(min_value=1, max_value=max(1, total_volume)))
        interval_seconds = draw(st.integers(min_value=1, max_value=3600))
        order = scheduler.submit_timed_split(instruction, interval_seconds, per_order_volume, start_time)
    elif order_type == "classic_iceberg":
        per_order_volume = draw(st.integers(min_value=1, max_value=max(1, total_volume)))
        order = scheduler.submit_classic_iceberg(instruction, per_order_volume)
    else:  # enhanced_twap
        num_slices = draw(st.integers(min_value=1, max_value=min(100, total_volume)))
        time_window_seconds = draw(st.integers(min_value=1, max_value=86400))
        order = scheduler.submit_enhanced_twap(instruction, time_window_seconds, num_slices, start_time)

    return scheduler, order


class TestFilledVolumeTrackingProperty:
    """Feature: order-splitting-algorithms, Property 7: 成交量追踪不变量"""

    @given(data=st.data())
    @settings(max_examples=100)
    def test_property7_filled_volume_invariant(self, data):
        """
        **Validates: Requirements 4.1, 4.2**

        For any order type and any child fill sequence,
        filled_volume always equals the sum of volumes of all filled children.
        """
        scheduler, order = data.draw(order_type_strategy())
        child_ids = [c.child_id for c in order.child_orders]

        # 随机选择一个子集并打乱顺序作为成交序列
        num_to_fill = data.draw(st.integers(min_value=0, max_value=len(child_ids)))
        fill_indices = data.draw(
            st.permutations(range(len(child_ids))).map(lambda p: list(p[:num_to_fill]))
        )

        filled_set = set()
        for idx in fill_indices:
            child_id = child_ids[idx]
            scheduler.on_child_filled(child_id)
            filled_set.add(idx)

            # 不变量: filled_volume == 所有已成交子单的 volume 之和
            expected_filled = sum(
                order.child_orders[i].volume for i in filled_set
            )
            assert order.filled_volume == expected_filled, (
                f"After filling child {idx} ({child_id}): "
                f"filled_volume={order.filled_volume}, expected={expected_filled}"
            )



# --- Strategies for Property 7 ---

@st.composite
def order_type_strategy(draw):
    """随机选择一种新订单类型并生成对应的有效参数和订单"""
    order_type = draw(st.sampled_from(["timed_split", "classic_iceberg", "enhanced_twap"]))
    total_volume = draw(st.integers(min_value=1, max_value=500))
    instruction = make_instruction(total_volume)
    scheduler = AdvancedOrderScheduler()
    start_time = datetime(2025, 1, 1, 10, 0, 0)

    if order_type == "timed_split":
        per_order_volume = draw(st.integers(min_value=1, max_value=max(1, total_volume)))
        interval_seconds = draw(st.integers(min_value=1, max_value=3600))
        order = scheduler.submit_timed_split(instruction, interval_seconds, per_order_volume, start_time)
    elif order_type == "classic_iceberg":
        per_order_volume = draw(st.integers(min_value=1, max_value=max(1, total_volume)))
        order = scheduler.submit_classic_iceberg(instruction, per_order_volume)
    else:  # enhanced_twap
        num_slices = draw(st.integers(min_value=1, max_value=min(100, total_volume)))
        time_window_seconds = draw(st.integers(min_value=1, max_value=86400))
        order = scheduler.submit_enhanced_twap(instruction, time_window_seconds, num_slices, start_time)

    return scheduler, order


class TestFilledVolumeTrackingProperty:
    """Feature: order-splitting-algorithms, Property 7: 成交量追踪不变量"""

    @given(data=st.data())
    @settings(max_examples=100)
    def test_property7_filled_volume_invariant(self, data):
        """
        **Validates: Requirements 4.1, 4.2**

        For any order type and any child fill sequence,
        filled_volume always equals the sum of volumes of all filled children.
        """
        scheduler, order = data.draw(order_type_strategy())
        child_ids = [c.child_id for c in order.child_orders]

        # 随机选择一个子集并打乱顺序作为成交序列
        num_to_fill = data.draw(st.integers(min_value=0, max_value=len(child_ids)))
        fill_indices = data.draw(
            st.permutations(range(len(child_ids))).map(lambda p: list(p[:num_to_fill]))
        )

        filled_set = set()
        for idx in fill_indices:
            child_id = child_ids[idx]
            scheduler.on_child_filled(child_id)
            filled_set.add(idx)

            # 不变量: filled_volume == 所有已成交子单的 volume 之和
            expected_filled = sum(
                order.child_orders[i].volume for i in filled_set
            )
            assert order.filled_volume == expected_filled, (
                f"After filling child {idx} ({child_id}): "
                f"filled_volume={order.filled_volume}, expected={expected_filled}"
            )
