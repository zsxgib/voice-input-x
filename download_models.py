#!/usr/bin/env python3
"""
下载 Whisper 模型 (使用代理)

用法: proxychains4 python download_models.py
"""

import sys
import os
import shutil
import httpx
from tqdm import tqdm

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from huggingface_hub import snapshot_download
import torch

MODELS = ["tiny", "base", "small", "medium", "large-v3"]

CACHE_BASE = os.path.expanduser("~/.cache/huggingface/hub")


def get_device():
    """获取可用设备"""
    if torch.cuda.is_available():
        print(f"✓ GPU: {torch.cuda.get_device_name(0)}")
        return "cuda"
    else:
        print("⚠ 无 GPU，使用 CPU")
        return "cpu"


def get_model_id(model_name):
    """获取模型ID"""
    return f"Systran/faster-whisper-{model_name}"


def clean_model(model_name):
    """清理损坏的模型缓存"""
    model_id = get_model_id(model_name).replace("/", "--")
    model_dir = os.path.join(CACHE_BASE, f"models--{model_id}")
    if os.path.exists(model_dir):
        print(f"  清理旧缓存: {model_dir}")
        shutil.rmtree(model_dir)


def download_with_progress(model_name):
    """带进度下载模型"""
    model_id = get_model_id(model_name)
    print(f"\n[{model_name}] 开始下载...")

    try:
        # 清理可能损坏的缓存
        clean_model(model_name)

        print(f"  正在下载 {model_id}...")

        # 使用 huggingface_hub 直接下载
        local_dir = snapshot_download(
            repo_id=model_id,
            cache_dir=CACHE_BASE,
            force_download=True,
            resume_download=True,
        )

        print(f"  ✓ {model_name} 下载完成!")
        print(f"    路径: {local_dir}")
        return True

    except Exception as e:
        print(f"  ✗ {model_name} 下载失败: {e}")
        return False


def main():
    print("=" * 50)
    print("       Whisper 模型下载器")
    print("=" * 50)
    print("使用: proxychains4 python download_models.py")

    get_device()

    # 下载所有模型
    success = 0
    for i, model_name in enumerate(MODELS):
        print(f"\n[{i+1}/{len(MODELS)}] ", end="", flush=True)
        if download_with_progress(model_name):
            success += 1

    print(f"\n{'='*50}")
    print(f"完成! 成功 {success}/{len(MODELS)}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
