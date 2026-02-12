"""SnapshotJsonTransformer.resolve_special_markers 单元测试"""

import pytest
from src.web.reader import SnapshotJsonTransformer


class TestResolveSpecialMarkers:
    """测试 resolve_special_markers 方法"""

    # --- 基本类型直接返回 ---

    def test_primitive_string(self):
        assert SnapshotJsonTransformer.resolve_special_markers("hello") == "hello"

    def test_primitive_int(self):
        assert SnapshotJsonTransformer.resolve_special_markers(42) == 42

    def test_primitive_float(self):
        assert SnapshotJsonTransformer.resolve_special_markers(3.14) == 3.14

    def test_primitive_bool(self):
        assert SnapshotJsonTransformer.resolve_special_markers(True) is True

    def test_primitive_none(self):
        assert SnapshotJsonTransformer.resolve_special_markers(None) is None

    # --- __dataframe__ 标记 ---

    def test_dataframe_marker(self):
        obj = {"__dataframe__": True, "records": [{"a": 1}, {"a": 2}]}
        result = SnapshotJsonTransformer.resolve_special_markers(obj)
        assert result == [{"a": 1}, {"a": 2}]

    def test_dataframe_marker_empty_records(self):
        obj = {"__dataframe__": True, "records": []}
        assert SnapshotJsonTransformer.resolve_special_markers(obj) == []

    def test_dataframe_marker_no_records_key(self):
        obj = {"__dataframe__": True}
        assert SnapshotJsonTransformer.resolve_special_markers(obj) == []

    # --- __datetime__ 标记 ---

    def test_datetime_marker_with_timezone(self):
        obj = {"__datetime__": "2025-01-15T14:29:00+08:00"}
        result = SnapshotJsonTransformer.resolve_special_markers(obj)
        assert result == "2025-01-15 14:29:00"

    def test_datetime_marker_without_timezone(self):
        obj = {"__datetime__": "2025-01-15T14:29:00"}
        result = SnapshotJsonTransformer.resolve_special_markers(obj)
        assert result == "2025-01-15 14:29:00"

    def test_datetime_marker_invalid_format(self):
        obj = {"__datetime__": "not-a-date"}
        result = SnapshotJsonTransformer.resolve_special_markers(obj)
        assert result == "not-a-date"

    # --- __date__ 标记 ---

    def test_date_marker(self):
        obj = {"__date__": "2025-01-15"}
        assert SnapshotJsonTransformer.resolve_special_markers(obj) == "2025-01-15"

    # --- __enum__ 标记 ---

    def test_enum_marker(self):
        obj = {"__enum__": "Direction.LONG"}
        assert SnapshotJsonTransformer.resolve_special_markers(obj) == "Direction.LONG"

    # --- __set__ 标记 ---

    def test_set_marker(self):
        obj = {"__set__": True, "values": [1, 2, 3]}
        assert SnapshotJsonTransformer.resolve_special_markers(obj) == [1, 2, 3]

    def test_set_marker_empty(self):
        obj = {"__set__": True, "values": []}
        assert SnapshotJsonTransformer.resolve_special_markers(obj) == []

    def test_set_marker_no_values_key(self):
        obj = {"__set__": True}
        assert SnapshotJsonTransformer.resolve_special_markers(obj) == []

    # --- __dataclass__ 标记 ---

    def test_dataclass_marker(self):
        obj = {"__dataclass__": "module.ClassName", "a": 1, "b": "hello"}
        result = SnapshotJsonTransformer.resolve_special_markers(obj)
        assert result == {"a": 1, "b": "hello"}

    def test_dataclass_marker_with_nested_markers(self):
        obj = {
            "__dataclass__": "module.Cls",
            "direction": {"__enum__": "Direction.LONG"},
            "count": 5,
        }
        result = SnapshotJsonTransformer.resolve_special_markers(obj)
        assert result == {"direction": "Direction.LONG", "count": 5}

    # --- 递归解析 ---

    def test_nested_dict(self):
        obj = {
            "level1": {
                "dt": {"__datetime__": "2025-01-15T10:00:00"},
                "val": 42,
            }
        }
        result = SnapshotJsonTransformer.resolve_special_markers(obj)
        assert result == {"level1": {"dt": "2025-01-15 10:00:00", "val": 42}}

    def test_list_with_markers(self):
        obj = [
            {"__enum__": "Status.ACTIVE"},
            {"__date__": "2025-01-15"},
            "plain",
        ]
        result = SnapshotJsonTransformer.resolve_special_markers(obj)
        assert result == ["Status.ACTIVE", "2025-01-15", "plain"]

    def test_dataframe_with_nested_markers(self):
        obj = {
            "__dataframe__": True,
            "records": [
                {"dt": {"__datetime__": "2025-01-15T09:00:00"}, "value": 100},
            ],
        }
        result = SnapshotJsonTransformer.resolve_special_markers(obj)
        assert result == [{"dt": "2025-01-15 09:00:00", "value": 100}]

    def test_regular_dict_no_markers(self):
        obj = {"name": "test", "count": 3}
        assert SnapshotJsonTransformer.resolve_special_markers(obj) == {"name": "test", "count": 3}

    def test_unknown_marker_preserved(self):
        """未知标记应保留原始值（作为普通 dict 递归解析）"""
        obj = {"__unknown__": "something", "data": 1}
        result = SnapshotJsonTransformer.resolve_special_markers(obj)
        assert result == {"__unknown__": "something", "data": 1}
