"""
DomainServiceConfigLoader 属性测试

使用 Hypothesis 验证配置加载器的正确性属性。

Feature: domain-service-infrastructure-refactoring, Property 7: 配置加载正确性
验证需求: 6.2, 6.3, 6.4, 6.5
"""
import pytest
import importlib.util
from pathlib import Path
from hypothesis import given, strategies as st, settings

# 直接加载模块文件避免 __init__.py 的依赖问题
module_path = Path(__file__).parent.parent.parent.parent / "src" / "main" / "config" / "domain_service_config_loader.py"
spec = importlib.util.spec_from_file_location("domain_service_config_loader", module_path)
domain_service_config_loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(domain_service_config_loader)

from src.strategy.domain.domain_service.execution.smart_order_executor import SmartOrderExecutor
from src.strategy.domain.domain_service.execution.advanced_order_scheduler import AdvancedOrderScheduler
from src.strategy.domain.value_object.trading.order_execution import (
    OrderExecutionConfig,
    AdvancedSchedulerConfig,
)


# ============================================================================
# Hypothesis 策略定义
# ============================================================================

@st.composite
def partial_smart_executor_config_strategy(draw):
    """
    生成部分 SmartOrderExecutor 配置字典（可能缺失某些字段）
    
    这模拟了实际使用中配置文件可能只包含部分配置项的情况
    """
    config_dict = {}
    
    # 每个字段有 50% 的概率出现在配置中
    if draw(st.booleans()):
        config_dict["timeout_seconds"] = draw(st.integers(min_value=10, max_value=300))
    
    if draw(st.booleans()):
        config_dict["max_retries"] = draw(st.integers(min_value=0, max_value=10))
    
    if draw(st.booleans()):
        config_dict["slippage_ticks"] = draw(st.integers(min_value=0, max_value=10))
    
    if draw(st.booleans()):
        config_dict["price_tick"] = draw(st.floats(min_value=0.01, max_value=1.0))
    
    return config_dict


@st.composite
def partial_advanced_scheduler_config_strategy(draw):
    """
    生成部分 AdvancedOrderScheduler 配置字典（可能缺失某些字段）
    
    这模拟了实际使用中配置文件可能只包含部分配置项的情况
    """
    config_dict = {}
    
    # 每个字段有 50% 的概率出现在配置中
    if draw(st.booleans()):
        config_dict["default_batch_size"] = draw(st.integers(min_value=1, max_value=100))
    
    if draw(st.booleans()):
        config_dict["default_interval_seconds"] = draw(st.integers(min_value=1, max_value=300))
    
    if draw(st.booleans()):
        config_dict["default_num_slices"] = draw(st.integers(min_value=1, max_value=20))
    
    if draw(st.booleans()):
        config_dict["default_volume_randomize_ratio"] = draw(st.floats(min_value=0.0, max_value=0.5))
    
    if draw(st.booleans()):
        config_dict["default_price_offset_ticks"] = draw(st.integers(min_value=0, max_value=10))
    
    if draw(st.booleans()):
        config_dict["default_price_tick"] = draw(st.floats(min_value=0.01, max_value=1.0))
    
    return config_dict


# ============================================================================
# 属性 7: 配置加载正确性
# ============================================================================

class TestSmartOrderExecutorConfigLoadingProperties:
    """测试 SmartOrderExecutor 配置加载的正确性属性"""
    
    @given(config_dict=partial_smart_executor_config_strategy())
    @settings(max_examples=100)
    def test_property_loaded_config_matches_provided_values(self, config_dict):
        """
        属性: 对于配置字典中存在的配置项，加载的实例配置参数应该与配置字典中的值相同
        
        验证需求: 6.2, 6.5
        """
        # 创建实例
        executor = domain_service_config_loader.create_smart_order_executor(config_dict)
        
        # 验证: 配置字典中存在的字段，实例的配置参数应该与之相同
        if "timeout_seconds" in config_dict:
            assert executor.config.timeout_seconds == config_dict["timeout_seconds"], \
                f"timeout_seconds 不匹配: 期望 {config_dict['timeout_seconds']}, 实际 {executor.config.timeout_seconds}"
        
        if "max_retries" in config_dict:
            assert executor.config.max_retries == config_dict["max_retries"], \
                f"max_retries 不匹配: 期望 {config_dict['max_retries']}, 实际 {executor.config.max_retries}"
        
        if "slippage_ticks" in config_dict:
            assert executor.config.slippage_ticks == config_dict["slippage_ticks"], \
                f"slippage_ticks 不匹配: 期望 {config_dict['slippage_ticks']}, 实际 {executor.config.slippage_ticks}"
        
        if "price_tick" in config_dict:
            assert executor.config.price_tick == config_dict["price_tick"], \
                f"price_tick 不匹配: 期望 {config_dict['price_tick']}, 实际 {executor.config.price_tick}"
    
    @given(config_dict=partial_smart_executor_config_strategy())
    @settings(max_examples=100)
    def test_property_missing_fields_use_defaults(self, config_dict):
        """
        属性: 对于配置字典中缺失的配置项，加载的实例配置参数应该使用默认值
        
        验证需求: 6.4, 6.5
        """
        # 获取默认配置
        default_config = OrderExecutionConfig()
        
        # 创建实例
        executor = domain_service_config_loader.create_smart_order_executor(config_dict)
        
        # 验证: 配置字典中缺失的字段，实例应该使用默认值
        if "timeout_seconds" not in config_dict:
            assert executor.config.timeout_seconds == default_config.timeout_seconds, \
                f"timeout_seconds 应使用默认值 {default_config.timeout_seconds}, 实际 {executor.config.timeout_seconds}"
        
        if "max_retries" not in config_dict:
            assert executor.config.max_retries == default_config.max_retries, \
                f"max_retries 应使用默认值 {default_config.max_retries}, 实际 {executor.config.max_retries}"
        
        if "slippage_ticks" not in config_dict:
            assert executor.config.slippage_ticks == default_config.slippage_ticks, \
                f"slippage_ticks 应使用默认值 {default_config.slippage_ticks}, 实际 {executor.config.slippage_ticks}"
        
        if "price_tick" not in config_dict:
            assert executor.config.price_tick == default_config.price_tick, \
                f"price_tick 应使用默认值 {default_config.price_tick}, 实际 {executor.config.price_tick}"
    
    @given(config_dict=partial_smart_executor_config_strategy())
    @settings(max_examples=100)
    def test_property_created_instance_is_valid(self, config_dict):
        """
        属性: 加载的实例应该是有效的 SmartOrderExecutor 实例
        
        验证需求: 6.2, 6.3
        """
        executor = domain_service_config_loader.create_smart_order_executor(config_dict)
        
        # 验证实例类型
        assert isinstance(executor, SmartOrderExecutor), \
            f"期望 SmartOrderExecutor 实例, 实际 {type(executor)}"
        
        # 验证实例具有必要的属性和方法
        assert hasattr(executor, "config"), "实例缺少 config 属性"
        assert hasattr(executor, "register_order"), "实例缺少 register_order 方法"
        assert hasattr(executor, "mark_order_cancelled"), "实例缺少 mark_order_cancelled 方法"
        assert hasattr(executor, "check_timeouts"), "实例缺少 check_timeouts 方法"
        
        # 验证配置对象类型
        assert isinstance(executor.config, OrderExecutionConfig), \
            f"期望 OrderExecutionConfig 配置, 实际 {type(executor.config)}"


class TestAdvancedOrderSchedulerConfigLoadingProperties:
    """测试 AdvancedOrderScheduler 配置加载的正确性属性"""
    
    @given(config_dict=partial_advanced_scheduler_config_strategy())
    @settings(max_examples=100)
    def test_property_loaded_config_matches_provided_values(self, config_dict):
        """
        属性: 对于配置字典中存在的配置项，加载的实例配置参数应该与配置字典中的值相同
        
        验证需求: 6.3, 6.5
        """
        # 创建实例
        scheduler = domain_service_config_loader.create_advanced_order_scheduler(config_dict)
        
        # 验证: 配置字典中存在的字段，实例的配置参数应该与之相同
        if "default_batch_size" in config_dict:
            assert scheduler.config.default_batch_size == config_dict["default_batch_size"], \
                f"default_batch_size 不匹配: 期望 {config_dict['default_batch_size']}, 实际 {scheduler.config.default_batch_size}"
        
        if "default_interval_seconds" in config_dict:
            assert scheduler.config.default_interval_seconds == config_dict["default_interval_seconds"], \
                f"default_interval_seconds 不匹配: 期望 {config_dict['default_interval_seconds']}, 实际 {scheduler.config.default_interval_seconds}"
        
        if "default_num_slices" in config_dict:
            assert scheduler.config.default_num_slices == config_dict["default_num_slices"], \
                f"default_num_slices 不匹配: 期望 {config_dict['default_num_slices']}, 实际 {scheduler.config.default_num_slices}"
        
        if "default_volume_randomize_ratio" in config_dict:
            assert scheduler.config.default_volume_randomize_ratio == config_dict["default_volume_randomize_ratio"], \
                f"default_volume_randomize_ratio 不匹配: 期望 {config_dict['default_volume_randomize_ratio']}, 实际 {scheduler.config.default_volume_randomize_ratio}"
        
        if "default_price_offset_ticks" in config_dict:
            assert scheduler.config.default_price_offset_ticks == config_dict["default_price_offset_ticks"], \
                f"default_price_offset_ticks 不匹配: 期望 {config_dict['default_price_offset_ticks']}, 实际 {scheduler.config.default_price_offset_ticks}"
        
        if "default_price_tick" in config_dict:
            assert scheduler.config.default_price_tick == config_dict["default_price_tick"], \
                f"default_price_tick 不匹配: 期望 {config_dict['default_price_tick']}, 实际 {scheduler.config.default_price_tick}"
    
    @given(config_dict=partial_advanced_scheduler_config_strategy())
    @settings(max_examples=100)
    def test_property_missing_fields_use_defaults(self, config_dict):
        """
        属性: 对于配置字典中缺失的配置项，加载的实例配置参数应该使用默认值
        
        验证需求: 6.4, 6.5
        """
        # 获取默认配置
        default_config = AdvancedSchedulerConfig()
        
        # 创建实例
        scheduler = domain_service_config_loader.create_advanced_order_scheduler(config_dict)
        
        # 验证: 配置字典中缺失的字段，实例应该使用默认值
        if "default_batch_size" not in config_dict:
            assert scheduler.config.default_batch_size == default_config.default_batch_size, \
                f"default_batch_size 应使用默认值 {default_config.default_batch_size}, 实际 {scheduler.config.default_batch_size}"
        
        if "default_interval_seconds" not in config_dict:
            assert scheduler.config.default_interval_seconds == default_config.default_interval_seconds, \
                f"default_interval_seconds 应使用默认值 {default_config.default_interval_seconds}, 实际 {scheduler.config.default_interval_seconds}"
        
        if "default_num_slices" not in config_dict:
            assert scheduler.config.default_num_slices == default_config.default_num_slices, \
                f"default_num_slices 应使用默认值 {default_config.default_num_slices}, 实际 {scheduler.config.default_num_slices}"
        
        if "default_volume_randomize_ratio" not in config_dict:
            assert scheduler.config.default_volume_randomize_ratio == default_config.default_volume_randomize_ratio, \
                f"default_volume_randomize_ratio 应使用默认值 {default_config.default_volume_randomize_ratio}, 实际 {scheduler.config.default_volume_randomize_ratio}"
        
        if "default_price_offset_ticks" not in config_dict:
            assert scheduler.config.default_price_offset_ticks == default_config.default_price_offset_ticks, \
                f"default_price_offset_ticks 应使用默认值 {default_config.default_price_offset_ticks}, 实际 {scheduler.config.default_price_offset_ticks}"
        
        if "default_price_tick" not in config_dict:
            assert scheduler.config.default_price_tick == default_config.default_price_tick, \
                f"default_price_tick 应使用默认值 {default_config.default_price_tick}, 实际 {scheduler.config.default_price_tick}"
    
    @given(config_dict=partial_advanced_scheduler_config_strategy())
    @settings(max_examples=100)
    def test_property_created_instance_is_valid(self, config_dict):
        """
        属性: 加载的实例应该是有效的 AdvancedOrderScheduler 实例
        
        验证需求: 6.3, 6.5
        """
        scheduler = domain_service_config_loader.create_advanced_order_scheduler(config_dict)
        
        # 验证实例类型
        assert isinstance(scheduler, AdvancedOrderScheduler), \
            f"期望 AdvancedOrderScheduler 实例, 实际 {type(scheduler)}"
        
        # 验证实例具有必要的属性和方法
        assert hasattr(scheduler, "config"), "实例缺少 config 属性"
        assert hasattr(scheduler, "submit_iceberg"), "实例缺少 submit_iceberg 方法"
        assert hasattr(scheduler, "cancel_order"), "实例缺少 cancel_order 方法"
        assert hasattr(scheduler, "get_order"), "实例缺少 get_order 方法"
        
        # 验证配置对象类型
        assert isinstance(scheduler.config, AdvancedSchedulerConfig), \
            f"期望 AdvancedSchedulerConfig 配置, 实际 {type(scheduler.config)}"


class TestConfigLoadingEdgeCases:
    """测试配置加载的边界情况"""
    
    @settings(max_examples=100)
    @given(st.data())
    def test_property_empty_config_creates_valid_executor(self, data):
        """
        属性: 空配置字典应该创建使用全部默认值的有效实例
        
        验证需求: 6.4
        """
        config_dict = {}
        
        executor = domain_service_config_loader.create_smart_order_executor(config_dict)
        default_config = OrderExecutionConfig()
        
        assert executor.config.timeout_seconds == default_config.timeout_seconds
        assert executor.config.max_retries == default_config.max_retries
        assert executor.config.slippage_ticks == default_config.slippage_ticks
        assert executor.config.price_tick == default_config.price_tick
    
    @settings(max_examples=100)
    @given(st.data())
    def test_property_empty_config_creates_valid_scheduler(self, data):
        """
        属性: 空配置字典应该创建使用全部默认值的有效实例
        
        验证需求: 6.4
        """
        config_dict = {}
        
        scheduler = domain_service_config_loader.create_advanced_order_scheduler(config_dict)
        default_config = AdvancedSchedulerConfig()
        
        assert scheduler.config.default_batch_size == default_config.default_batch_size
        assert scheduler.config.default_interval_seconds == default_config.default_interval_seconds
        assert scheduler.config.default_num_slices == default_config.default_num_slices
        assert scheduler.config.default_volume_randomize_ratio == default_config.default_volume_randomize_ratio
        assert scheduler.config.default_price_offset_ticks == default_config.default_price_offset_ticks
        assert scheduler.config.default_price_tick == default_config.default_price_tick
