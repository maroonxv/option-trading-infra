"""
DomainServiceConfigLoader 单元测试

测试从配置字典创建领域服务实例的工厂方法。
"""
import pytest
import importlib.util
from pathlib import Path

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


class TestCreateSmartOrderExecutor:
    """测试 create_smart_order_executor 工厂方法"""
    
    def test_create_with_full_config(self):
        """测试使用完整配置创建实例"""
        config_dict = {
            "timeout_seconds": 30,
            "max_retries": 3,
            "slippage_ticks": 2,
            "price_tick": 0.2,
        }
        
        executor = domain_service_config_loader.create_smart_order_executor(config_dict)
        
        assert isinstance(executor, SmartOrderExecutor)
        assert executor.config.timeout_seconds == 30
        assert executor.config.max_retries == 3
        assert executor.config.slippage_ticks == 2
        assert executor.config.price_tick == 0.2
    
    def test_create_with_partial_config(self):
        """测试使用部分配置创建实例（缺失字段使用默认值）"""
        config_dict = {
            "timeout_seconds": 60,
            "max_retries": 5,
        }
        
        executor = domain_service_config_loader.create_smart_order_executor(config_dict)
        
        assert isinstance(executor, SmartOrderExecutor)
        assert executor.config.timeout_seconds == 60
        assert executor.config.max_retries == 5
        # 缺失的字段应使用默认值
        assert executor.config.slippage_ticks == OrderExecutionConfig().slippage_ticks
        assert executor.config.price_tick == OrderExecutionConfig().price_tick
    
    def test_create_with_empty_config(self):
        """测试使用空配置创建实例（全部使用默认值）"""
        config_dict = {}
        
        executor = domain_service_config_loader.create_smart_order_executor(config_dict)
        
        assert isinstance(executor, SmartOrderExecutor)
        # 所有字段应使用默认值
        default_config = OrderExecutionConfig()
        assert executor.config.timeout_seconds == default_config.timeout_seconds
        assert executor.config.max_retries == default_config.max_retries
        assert executor.config.slippage_ticks == default_config.slippage_ticks
        assert executor.config.price_tick == default_config.price_tick
    
    def test_create_with_single_field(self):
        """测试只提供单个配置字段"""
        config_dict = {"timeout_seconds": 120}
        
        executor = domain_service_config_loader.create_smart_order_executor(config_dict)
        
        assert isinstance(executor, SmartOrderExecutor)
        assert executor.config.timeout_seconds == 120
        # 其他字段使用默认值
        default_config = OrderExecutionConfig()
        assert executor.config.max_retries == default_config.max_retries
        assert executor.config.slippage_ticks == default_config.slippage_ticks
        assert executor.config.price_tick == default_config.price_tick
    
    def test_create_with_different_values(self):
        """测试使用不同的配置值"""
        config_dict = {
            "timeout_seconds": 15,
            "max_retries": 1,
            "slippage_ticks": 5,
            "price_tick": 0.5,
        }
        
        executor = domain_service_config_loader.create_smart_order_executor(config_dict)
        
        assert executor.config.timeout_seconds == 15
        assert executor.config.max_retries == 1
        assert executor.config.slippage_ticks == 5
        assert executor.config.price_tick == 0.5
    
    def test_created_executor_is_functional(self):
        """测试创建的执行器是可用的"""
        config_dict = {"timeout_seconds": 30}
        
        executor = domain_service_config_loader.create_smart_order_executor(config_dict)
        
        # 验证执行器的基本功能
        assert hasattr(executor, "config")
        assert hasattr(executor, "register_order")
        assert hasattr(executor, "mark_order_cancelled")
        assert hasattr(executor, "check_timeouts")


class TestCreateAdvancedOrderScheduler:
    """测试 create_advanced_order_scheduler 工厂方法"""
    
    def test_create_with_full_config(self):
        """测试使用完整配置创建实例"""
        config_dict = {
            "default_batch_size": 10,
            "default_interval_seconds": 60,
            "default_num_slices": 5,
            "default_volume_randomize_ratio": 0.1,
            "default_price_offset_ticks": 2,
            "default_price_tick": 0.2,
        }
        
        scheduler = domain_service_config_loader.create_advanced_order_scheduler(config_dict)
        
        assert isinstance(scheduler, AdvancedOrderScheduler)
        assert scheduler.config.default_batch_size == 10
        assert scheduler.config.default_interval_seconds == 60
        assert scheduler.config.default_num_slices == 5
        assert scheduler.config.default_volume_randomize_ratio == 0.1
        assert scheduler.config.default_price_offset_ticks == 2
        assert scheduler.config.default_price_tick == 0.2
    
    def test_create_with_partial_config(self):
        """测试使用部分配置创建实例（缺失字段使用默认值）"""
        config_dict = {
            "default_batch_size": 20,
            "default_interval_seconds": 120,
            "default_num_slices": 10,
        }
        
        scheduler = domain_service_config_loader.create_advanced_order_scheduler(config_dict)
        
        assert isinstance(scheduler, AdvancedOrderScheduler)
        assert scheduler.config.default_batch_size == 20
        assert scheduler.config.default_interval_seconds == 120
        assert scheduler.config.default_num_slices == 10
        # 缺失的字段应使用默认值
        default_config = AdvancedSchedulerConfig()
        assert scheduler.config.default_volume_randomize_ratio == default_config.default_volume_randomize_ratio
        assert scheduler.config.default_price_offset_ticks == default_config.default_price_offset_ticks
        assert scheduler.config.default_price_tick == default_config.default_price_tick
    
    def test_create_with_empty_config(self):
        """测试使用空配置创建实例（全部使用默认值）"""
        config_dict = {}
        
        scheduler = domain_service_config_loader.create_advanced_order_scheduler(config_dict)
        
        assert isinstance(scheduler, AdvancedOrderScheduler)
        # 所有字段应使用默认值
        default_config = AdvancedSchedulerConfig()
        assert scheduler.config.default_batch_size == default_config.default_batch_size
        assert scheduler.config.default_interval_seconds == default_config.default_interval_seconds
        assert scheduler.config.default_num_slices == default_config.default_num_slices
        assert scheduler.config.default_volume_randomize_ratio == default_config.default_volume_randomize_ratio
        assert scheduler.config.default_price_offset_ticks == default_config.default_price_offset_ticks
        assert scheduler.config.default_price_tick == default_config.default_price_tick
    
    def test_create_with_single_field(self):
        """测试只提供单个配置字段"""
        config_dict = {"default_batch_size": 50}
        
        scheduler = domain_service_config_loader.create_advanced_order_scheduler(config_dict)
        
        assert isinstance(scheduler, AdvancedOrderScheduler)
        assert scheduler.config.default_batch_size == 50
        # 其他字段使用默认值
        default_config = AdvancedSchedulerConfig()
        assert scheduler.config.default_interval_seconds == default_config.default_interval_seconds
        assert scheduler.config.default_num_slices == default_config.default_num_slices
    
    def test_create_with_different_values(self):
        """测试使用不同的配置值"""
        config_dict = {
            "default_batch_size": 5,
            "default_interval_seconds": 30,
            "default_num_slices": 3,
            "default_volume_randomize_ratio": 0.2,
            "default_price_offset_ticks": 1,
            "default_price_tick": 0.1,
        }
        
        scheduler = domain_service_config_loader.create_advanced_order_scheduler(config_dict)
        
        assert scheduler.config.default_batch_size == 5
        assert scheduler.config.default_interval_seconds == 30
        assert scheduler.config.default_num_slices == 3
        assert scheduler.config.default_volume_randomize_ratio == 0.2
        assert scheduler.config.default_price_offset_ticks == 1
        assert scheduler.config.default_price_tick == 0.1
    
    def test_created_scheduler_is_functional(self):
        """测试创建的调度器是可用的"""
        config_dict = {"default_batch_size": 10}
        
        scheduler = domain_service_config_loader.create_advanced_order_scheduler(config_dict)
        
        # 验证调度器的基本功能
        assert hasattr(scheduler, "config")
        assert hasattr(scheduler, "submit_iceberg")
        assert hasattr(scheduler, "cancel_order")
        assert hasattr(scheduler, "get_order")


class TestConfigLoaderIntegration:
    """测试配置加载器的集成场景"""
    
    def test_create_both_services_with_same_price_tick(self):
        """测试创建两个服务使用相同的 price_tick"""
        price_tick = 0.25
        
        executor_config = {"price_tick": price_tick}
        scheduler_config = {"default_price_tick": price_tick}
        
        executor = domain_service_config_loader.create_smart_order_executor(executor_config)
        scheduler = domain_service_config_loader.create_advanced_order_scheduler(scheduler_config)
        
        assert executor.config.price_tick == price_tick
        assert scheduler.config.default_price_tick == price_tick
    
    def test_create_multiple_instances_with_different_configs(self):
        """测试创建多个实例使用不同配置"""
        config1 = {"timeout_seconds": 30}
        config2 = {"timeout_seconds": 60}
        
        executor1 = domain_service_config_loader.create_smart_order_executor(config1)
        executor2 = domain_service_config_loader.create_smart_order_executor(config2)
        
        assert executor1.config.timeout_seconds == 30
        assert executor2.config.timeout_seconds == 60
        # 验证是不同的实例
        assert executor1 is not executor2
    
    def test_config_dict_not_modified(self):
        """测试配置字典不被修改"""
        config_dict = {"timeout_seconds": 30}
        original_dict = config_dict.copy()
        
        domain_service_config_loader.create_smart_order_executor(config_dict)
        
        # 验证原始字典未被修改
        assert config_dict == original_dict
