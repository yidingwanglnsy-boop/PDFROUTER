# Copyright (c) Opendatalab. All rights reserved.
"""
IO工具函数模块
处理文件路径验证、文件读取、异常处理等通用IO操作
"""
import os
from pathlib import Path
from typing import Union, Optional

def validate_pdf_path(pdf_path: str) -> bool:
    """
    验证PDF路径是否合法存在
    :param pdf_path: PDF文件路径
    :return: 是否合法
    """
    if not pdf_path or not isinstance(pdf_path, str):
        return False
    path = Path(pdf_path)
    return path.exists() and path.is_file() and path.suffix.lower() == '.pdf'

def read_pdf_to_bytes(pdf_input: Union[str, bytes]) -> Optional[bytes]:
    """
    读取PDF内容，支持路径和bytes两种输入
    :param pdf_input: PDF文件路径或PDF二进制内容
    :return: PDF bytes，失败返回None
    """
    if isinstance(pdf_input, bytes):
        return pdf_input
    if isinstance(pdf_input, str):
        if not validate_pdf_path(pdf_input):
            return None
        try:
            with open(pdf_input, 'rb') as f:
                return f.read()
        except Exception:
            return None
    return None

def get_file_name_from_path(file_path: str) -> str:
    """
    从路径中提取文件名（不含后缀）
    :param file_path: 文件路径
    :return: 文件名
    """
    return Path(file_path).stem
