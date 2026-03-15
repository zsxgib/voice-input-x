# 日志模块

import logging
import sys


def setup_logger(name: str = "voice_input", level: int = logging.INFO) -> logging.Logger:
    """创建并配置日志器"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    # 控制台输出
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)

    # 格式化
    formatter = logging.Formatter(
        "[%(asctime)s] %(message)s",
        datefmt="%H:%M:%S"
    )
    console.setFormatter(formatter)

    logger.addHandler(console)

    return logger


# 全局日志实例
logger = setup_logger()
