"""
VnpyConnectionGateway - 连接管理网关

封装 vnpy MainEngine 的连接状态查询和重连能力。
"""
from typing import List, Optional, Dict, Any
from .vnpy_gateway_adapter import VnpyGatewayAdapter


class VnpyConnectionGateway(VnpyGatewayAdapter):
    """
    连接管理网关
    
    封装连接管理能力，包括：
    - 连接状态查询
    - 网关列表查询
    - 重新连接
    """
    
    def is_connected(self, gateway_name: str) -> bool:
        """
        检查指定网关的连接状态
        
        Args:
            gateway_name: 网关名称
            
        Returns:
            是否已连接
        """
        if not self.main_engine:
            self._log(f"MainEngine 不可用，无法检查连接状态: {gateway_name}")
            return False
        
        try:
            gateway = self.main_engine.get_gateway(gateway_name)
            if not gateway:
                self._log(f"找不到网关: {gateway_name}")
                return False
            
            # 尝试检查 td_api 和 md_api 的连接状态
            # CTP 网关有 td_api.connect_status 和 md_api.connect_status
            td_api = getattr(gateway, "td_api", None)
            md_api = getattr(gateway, "md_api", None)
            
            td_connected = getattr(td_api, "connect_status", False) if td_api else False
            md_connected = getattr(md_api, "connect_status", False) if md_api else False
            
            # 如果没有 td_api/md_api，尝试其他方式
            if not td_api and not md_api:
                # 尝试检查是否有 connect_status 属性
                return bool(getattr(gateway, "connect_status", False))
            
            return td_connected or md_connected
            
        except Exception as e:
            self._log(f"检查连接状态失败: {gateway_name}, 错误: {e}")
            return False
    
    def get_all_gateway_names(self) -> List[str]:
        """
        获取所有已添加网关的名称
        
        Returns:
            网关名称列表
        """
        if not self.main_engine:
            self._log("MainEngine 不可用，无法获取网关列表")
            return []
        
        try:
            return self.main_engine.get_all_gateway_names()
        except Exception as e:
            self._log(f"获取网关列表失败: {e}")
            return []
    
    def reconnect(self, gateway_name: str, setting: Dict[str, Any]) -> bool:
        """
        重新连接指定网关
        
        Args:
            gateway_name: 网关名称
            setting: 连接配置字典
            
        Returns:
            是否成功发起重连（注意：这只表示请求已发送，不代表连接成功）
        """
        if not self.main_engine:
            self._log(f"MainEngine 不可用，无法重连: {gateway_name}")
            return False
        
        try:
            gateway = self.main_engine.get_gateway(gateway_name)
            if not gateway:
                self._log(f"找不到网关: {gateway_name}")
                return False
            
            # 调用 connect 方法重新连接
            self.main_engine.connect(setting, gateway_name)
            self._log(f"已发起重连请求: {gateway_name}")
            return True
            
        except Exception as e:
            self._log(f"重连失败: {gateway_name}, 错误: {e}")
            return False
    
    def get_gateway_status(self, gateway_name: str) -> Dict[str, Any]:
        """
        获取网关详细状态
        
        Args:
            gateway_name: 网关名称
            
        Returns:
            状态字典，包含 td_connected、md_connected、login_status 等
        """
        status = {
            "gateway_name": gateway_name,
            "td_connected": False,
            "md_connected": False,
            "td_login": False,
            "md_login": False,
            "auth_status": False,
        }
        
        if not self.main_engine:
            return status
        
        try:
            gateway = self.main_engine.get_gateway(gateway_name)
            if not gateway:
                return status
            
            # 获取 td_api 状态
            td_api = getattr(gateway, "td_api", None)
            if td_api:
                status["td_connected"] = bool(getattr(td_api, "connect_status", False))
                status["td_login"] = bool(getattr(td_api, "login_status", False))
                status["auth_status"] = bool(getattr(td_api, "auth_status", False))
            
            # 获取 md_api 状态
            md_api = getattr(gateway, "md_api", None)
            if md_api:
                status["md_connected"] = bool(getattr(md_api, "connect_status", False))
                status["md_login"] = bool(getattr(md_api, "login_status", False))
            
        except Exception as e:
            self._log(f"获取网关状态失败: {gateway_name}, 错误: {e}")
        
        return status
    
    def get_default_setting(self, gateway_name: str) -> Optional[Dict[str, Any]]:
        """
        获取网关的默认配置
        
        Args:
            gateway_name: 网关名称
            
        Returns:
            默认配置字典，如果不存在则返回 None
        """
        if not self.main_engine:
            self._log(f"MainEngine 不可用，无法获取默认配置: {gateway_name}")
            return None
        
        try:
            return self.main_engine.get_default_setting(gateway_name)
        except Exception as e:
            self._log(f"获取默认配置失败: {gateway_name}, 错误: {e}")
            return None
