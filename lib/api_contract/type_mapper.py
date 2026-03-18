"""
Type Mapper - 跨语言类型映射器
处理 Python ↔ TypeScript 类型转换
"""

import re
from typing import Dict, List, Tuple, Optional
from .types import FieldType, TypeMappingRule, DEFAULT_TYPE_MAPPING, REVERSE_TYPE_MAPPING


class TypeMapper:
    """跨语言类型映射器"""
    
    def __init__(self, custom_mappings: Dict[str, str] = None):
        self.mappings = DEFAULT_TYPE_MAPPING.copy()
        if custom_mappings:
            self.mappings.update(custom_mappings)
    
    def python_to_typescript(self, python_type: str) -> str:
        """
        将 Python 类型转换为 TypeScript 类型
        
        Args:
            python_type: Python 类型字符串，如 "List[str]", "Optional[int]"
            
        Returns:
            TypeScript 类型字符串
        """
        # 处理泛型类型
        if '[' in python_type:
            return self._parse_generic_type(python_type)
        
        # 基础类型映射
        return self.mappings.get(python_type, python_type)
    
    def typescript_to_python(self, ts_type: str) -> str:
        """
        将 TypeScript 类型转换为 Python 类型
        
        Args:
            ts_type: TypeScript 类型字符串，如 "string[]", "number | null"
            
        Returns:
            Python 类型字符串
        """
        # 处理数组类型
        if ts_type.endswith('[]'):
            item_type = ts_type[:-2]
            python_item = REVERSE_TYPE_MAPPING.get(item_type, item_type)
            return f"List[{python_item}]"
        
        # 处理联合类型
        if '|' in ts_type:
            return self._parse_union_type(ts_type)
        
        # 处理可选类型
        if ts_type.endswith(' | undefined'):
            base_type = ts_type.replace(' | undefined', '')
            python_base = REVERSE_TYPE_MAPPING.get(base_type, base_type)
            return f"Optional[{python_base}]"
        
        # 基础类型映射
        return REVERSE_TYPE_MAPPING.get(ts_type, ts_type)
    
    def are_types_compatible(self, python_type: str, ts_type: str) -> bool:
        """
        检查两种类型是否兼容
        
        Args:
            python_type: Python 类型
            ts_type: TypeScript 类型
            
        Returns:
            是否兼容
        """
        # 转换为标准表示后比较
        py_normalized = self._normalize_python_type(python_type)
        ts_normalized = self._normalize_typescript_type(ts_type)
        
        return py_normalized == ts_normalized
    
    def get_type_mismatch_reason(self, python_type: str, ts_type: str) -> str:
        """
        获取类型不匹配的原因
        
        Args:
            python_type: Python 类型
            ts_type: TypeScript 类型
            
        Returns:
            不匹配原因描述
        """
        py_normalized = self._normalize_python_type(python_type)
        ts_normalized = self._normalize_typescript_type(ts_type)
        
        if py_normalized != ts_normalized:
            return f"类型不匹配: Python '{python_type}' ({py_normalized}) vs TypeScript '{ts_type}' ({ts_normalized})"
        return ""
    
    def _parse_generic_type(self, python_type: str) -> str:
        """解析 Python 泛型类型"""
        # 提取基础类型和参数
        match = re.match(r'(\w+)\[(.+)\]', python_type)
        if not match:
            return self.mappings.get(python_type, python_type)
        
        base_type = match.group(1)
        params = match.group(2)
        
        # 处理 Optional[T] -> T | undefined
        if base_type == 'Optional':
            inner = self.python_to_typescript(params)
            return f"{inner} | undefined"
        
        # 处理 List[T] -> T[]
        if base_type in ('List', 'list'):
            inner = self.python_to_typescript(params)
            return f"{inner}[]"
        
        # 处理 Dict[K, V] -> Record<K, V>
        if base_type in ('Dict', 'dict'):
            parts = [p.strip() for p in params.split(',')]
            if len(parts) == 2:
                key_type = self.python_to_typescript(parts[0])
                value_type = self.python_to_typescript(parts[1])
                return f"Record<{key_type}, {value_type}>"
        
        # 处理 Union[T1, T2] -> T1 | T2
        if base_type == 'Union':
            parts = [p.strip() for p in params.split(',')]
            ts_parts = [self.python_to_typescript(p) for p in parts]
            return ' | '.join(ts_parts)
        
        # 默认处理
        return self.mappings.get(python_type, python_type)
    
    def _parse_union_type(self, ts_type: str) -> str:
        """解析 TypeScript 联合类型"""
        parts = [p.strip() for p in ts_type.split('|')]
        
        # 检查是否包含 null/undefined（对应 Optional）
        has_null = 'null' in parts
        has_undefined = 'undefined' in parts
        
        # 提取非空类型
        non_null_parts = [p for p in parts if p not in ('null', 'undefined')]
        
        if len(non_null_parts) == 1:
            python_type = REVERSE_TYPE_MAPPING.get(non_null_parts[0], non_null_parts[0])
            if has_null or has_undefined:
                return f"Optional[{python_type}]"
            return python_type
        else:
            # 多类型联合
            python_parts = [REVERSE_TYPE_MAPPING.get(p, p) for p in non_null_parts]
            union_str = ', '.join(python_parts)
            if has_null or has_undefined:
                return f"Optional[Union[{union_str}]]"
            return f"Union[{union_str}]"
    
    def _normalize_python_type(self, python_type: str) -> str:
        """标准化 Python 类型（用于比较）"""
        # 移除空格
        normalized = python_type.replace(' ', '')
        
        # 转换为 TypeScript 类型
        return self.python_to_typescript(normalized)
    
    def _normalize_typescript_type(self, ts_type: str) -> str:
        """标准化 TypeScript 类型（用于比较）"""
        # 移除空格
        normalized = ts_type.replace(' ', '')
        
        # 统一可选类型表示
        normalized = normalized.replace('|undefined', '|null')
        normalized = normalized.replace('?','|null')
        
        return normalized
    
    def add_custom_mapping(self, python_type: str, ts_type: str):
        """添加自定义类型映射"""
        self.mappings[python_type] = ts_type
    
    def get_mapping_table(self) -> List[TypeMappingRule]:
        """获取完整映射表"""
        rules = []
        for py_type, ts_type in self.mappings.items():
            rules.append(TypeMappingRule(
                python_type=py_type,
                typescript_type=ts_type,
                is_compatible=True
            ))
        return rules


# 便捷函数
def map_python_to_typescript(python_type: str) -> str:
    """便捷函数：Python → TypeScript"""
    mapper = TypeMapper()
    return mapper.python_to_typescript(python_type)


def map_typescript_to_python(ts_type: str) -> str:
    """便捷函数：TypeScript → Python"""
    mapper = TypeMapper()
    return mapper.typescript_to_python(ts_type)


def check_type_compatibility(python_type: str, ts_type: str) -> bool:
    """便捷函数：检查类型兼容性"""
    mapper = TypeMapper()
    return mapper.are_types_compatible(python_type, ts_type)
