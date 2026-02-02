import os
import pickle
from typing import Any, Dict, Optional
from logging import Logger

class StateRepository:
    """
    负责策略状态的持久化 (保存与加载)
    """
    
    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger

    def save(self, file_path: str, data: Dict[str, Any]) -> None:
        """
        保存状态数据到文件 (原子操作)
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Use temp file for atomic write to prevent corruption
            temp_path = file_path + ".tmp"
            with open(temp_path, "wb") as f:
                pickle.dump(data, f)
            
            # Atomic replace
            if os.path.exists(file_path):
                try:
                    os.replace(temp_path, file_path)
                except OSError:
                    # If replace fails, try to remove temp and log error
                    if self.logger:
                        self.logger.error(f"Failed to replace state file: {file_path}")
                    try:
                        os.remove(temp_path)
                    except:
                        pass
            else:
                os.rename(temp_path, file_path)
            
            if self.logger:
                self.logger.info(f"策略状态已保存至: {file_path}")
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"保存策略状态失败: {str(e)}")

    def load(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        从文件加载状态数据
        """
        if not os.path.exists(file_path):
            if self.logger:
                self.logger.warning(f"未找到状态存档: {file_path}")
            return None
            
        try:
            with open(file_path, "rb") as f:
                state = pickle.load(f)
            
            if self.logger:
                self.logger.info(f"策略状态已从 {file_path} 恢复")
            return state
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"恢复策略状态失败: {str(e)}")
            return None
