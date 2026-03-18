"""
BMAD-EVO Type Mapper
Phase 2 MVP - Python ↔ TypeScript 类型映射
"""

import re
from typing import Dict, List, Optional, Tuple

from api_contract.types import FieldType, TypeMappingRule


class TypeMapper:
    """
    Python ↔ TypeScript 类型映射器
    
    默认映射规则:
        Python str         → TypeScript string
        Python int         → TypeScript number
        Python float       → TypeScript number
        Python bool        → TypeScript boolean
        Python list[T]     → TypeScript T[]
        Python List[T]     → TypeScript T[]
        Python dict[K,V]   → TypeScript Record<K, V>
        Python Dict[K,V]   → TypeScript Record<K, V>
        Python Optional[T] → TypeScript T | undefined
        Python datetime    → TypeScript string (ISO8601)
        Python UUID        → TypeScript string
    """
    
    DEFAULT_MAPPING: Dict[str, str] = {
        # 基础类型
        'str': 'string',
        'string': 'string',
        'int': 'number',
        'integer': 'number',
        'float': 'number',
        'bool': 'boolean',
        'boolean': 'boolean',
        'None': 'null',
        'NoneType': 'null',
        'Any': 'any',
        
        # 容器类型
        'list': 'array',
        'List': 'array',
        'dict': 'object',
        'Dict': 'object',
        'tuple': 'array',
        'Tuple': 'array',
        'set': 'array',
        'Set': 'array',
        
        # 特殊类型
        'datetime': 'string',
        'date': 'string',
        'UUID': 'string',
        'EmailStr': 'string',
        'HttpUrl': 'string',
        'Path': 'string',
    }
    
    # TypeScript → Python 反向映射
    REVERSE_MAPPING: Dict[str, str] = {
        'string': 'str',
        'number': 'float',
        'boolean': 'bool',
        'null': 'None',
        'any': 'Any',
        'array': 'List',
        'object': 'Dict',
        'undefined': 'Optional',
    }
    
    def __init__(self, custom_mapping: Optional[Dict[str, str]] = None):
        """
        初始化类型映射器
        
        Args:
            custom_mapping: 自定义类型映射规则
        """
        self.mapping = self.DEFAULT_MAPPING.copy()
        if custom_mapping:
            self.mapping.update(custom_mapping)
    
    def python_to_typescript(self, python_type: str) -> str:
        """
        Python 类型 → TypeScript 类型
        
        Args:
            python_type: Python 类型字符串，如 "List[str]", "Optional[int]"
            
        Returns:
            TypeScript 类型字符串
            
        示例:
            >>> mapper.python_to_typescript("str")
            "string"
            >>> mapper.python_to_typescript("List[str]")
            "string[]"
            >>> mapper.python_to_typescript("Optional[int]")
            "number | undefined"
        """
        python_type = python_type.strip()
        
        # 处理泛型类型
        if '[' in python_type:
            return self._parse_generic_type(python_type)
        
        # 基础类型映射
        return self.mapping.get(python_type, python_type)
    
    def typescript_to_python(self, ts_type: str) -> str:
        """
        TypeScript 类型 → Python 类型
        
        Args:
            ts_type: TypeScript 类型字符串，如 "string[]", "number | null"
            
        Returns:
            Python 类型字符串
        """
        ts_type = ts_type.strip()
        
        # 处理数组类型
        if ts_type.endswith('[]'):
            item_type = ts_type[:-2].strip()
            python_item = self.REVERSE_MAPPING.get(item_type, item_type)
            return f"List[{python_item}]"
        
        # 处理联合类型
        if '|' in ts_type:
            return self._parse_union_type(ts_type)
        
        # 处理可选类型
        if ts_type.endswith(' | undefined') or ts_type.endswith(' | null'):
            base_type = ts_type.rsplit(' |', 1)[0].strip()
            python_base = self.REVERSE_MAPPING.get(base_type, base_type)
            return f"Optional[{python_base}]"
        
        # 基础类型映射
        return self.REVERSE_MAPPING.get(ts_type, ts_type)
    
    def are_types_compatible(self, python_type: str, ts_type: str) -> bool:
        """
        检查两种类型是否兼容
        
        Args:
            python_type: Python 类型
            ts_type: TypeScript 类型
            
        Returns:
            是否兼容
            
        示例:
            >>> mapper.are_types_compatible("str", "string")
            True
            >>> mapper.are_types_compatible("int", "number")
            True
            >>> mapper.are_types_compatible("str", "number")
            False
        """
        # 标准化类型后比较
        py_normalized = self._normalize_python_type(python_type)
        ts_normalized = self._normalize_typescript_type(ts_type)
        
        # 直接相等
        if py_normalized == ts_normalized:
            return True
        
        # 处理特殊兼容情况
        # int/float 都可以对应 number
        if py_normalized in ('integer', 'number') and ts_normalized == 'number':
            return True
        
        # 处理可选类型
        py_optional = self._extract_optional_type(py_normalized)
        ts_optional = self._extract_optional_type(ts_normalized)
        
        if py_optional and ts_optional:
            return py_optional == ts_optional or \
                   (py_optional in ('integer', 'number') and ts_optional == 'number')
        
        return False
    
    def get_type_mismatch_reason(self, python_type: str, ts_type: str) -> str:
        """
        获取类型不匹配的原因
        
        Args:
            python_type: Python 类型
            ts_type: TypeScript 类型
            
        Returns:
            不匹配原因描述
        """
        if self.are_types_compatible(python_type, ts_type):
            return ""
        
        py_normalized = self._normalize_python_type(python_type)
        ts_normalized = self._normalize_typescript_type(ts_type)
        
        return (
            f"类型不匹配: Python '{python_type}' (标准化: {py_normalized}) "
            f"vs TypeScript '{ts_type}' (标准化: {ts_normalized})"
        )
    
    def _parse_generic_type(self, python_type: str) -> str:
        """解析 Python 泛型类型"""
        # 提取基础类型和参数
        match = re.match(r'(\w+)\[(.+)\]', python_type)
        if not match:
            return self.mapping.get(python_type, python_type)
        
        base_type = match.group(1)
        params = match.group(2).strip()
        
        # 处理 Optional[T] → T | undefined
        if base_type == 'Optional':
            inner = self.python_to_typescript(params)
            return f"{inner} | undefined"
        
        # 处理 List[T] → T[]
        if base_type in ('List', 'list'):
            inner = self.python_to_typescript(params)
            return f"{inner}[]"
        
        # 处理 Dict[K, V] → Record<K, V>
        if base_type in ('Dict', 'dict'):
            parts = [p.strip() for p in params.split(',')]
            if len(parts) == 2:
                key_type = self.python_to_typescript(parts[0])
                value_type = self.python_to_typescript(parts[1])
                return f"Record<{key_type}, {value_type}>"
        
        # 处理 Union[T1, T2] → T1 | T2
        if base_type == 'Union':
            parts = [p.strip() for p in params.split(',')]
            ts_parts = [self.python_to_typescript(p) for p in parts]
            return ' | '.join(ts_parts)
        
        # 默认处理：基础类型[参数]
        ts_base = self.mapping.get(base_type, base_type)
        ts_params = self.python_to_typescript(params)
        return f"{ts_base}<{ts_params}>"
    
    def _parse_union_type(self, ts_type: str) -> str:
        """解析 TypeScript 联合类型"""
        parts = [p.strip() for p in ts_type.split('|')]
        
        # 检查是否包含 null/undefined（对应 Optional）
        has_null = 'null' in parts
        has_undefined = 'undefined' in parts
        
        # 提取非空类型
        non_null_parts = [p for p in parts if p not in ('null', 'undefined')]
        
        if len(non_null_parts) == 1:
            python_type = self.REVERSE_MAPPING.get(non_null_parts[0], non_null_parts[0])
            if has_null or has_undefined:
                return f"Optional[{python_type}]"
            return python_type
        else:
            # 多类型联合
            python_parts = [self.REVERSE_MAPPING.get(p, p) for p in non_null_parts]
            union_str = ', '.join(python_parts)
            if has_null or has_undefined:
                return f"Optional[Union[{union_str}]]"
            return f"Union[{union_str}]"
    
    def _normalize_python_type(self, python_type: str) -> str:
        """标准化 Python 类型（用于比较）"""
        # 移除空格
        normalized = python_type.replace(' ', '')
        
        # 提取可选类型内部
        if normalized.startswith('Optional['):
            inner = normalized[9:-1]  # 提取 Optional[...] 内部
            return f"optional:{self._normalize_python_type(inner)}"
        
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
    
    def _extract_optional_type(self, normalized_type: str) -> Optional[str]:
        """提取可选类型的内部类型"""
        if normalized_type.startswith('optional:'):
            return normalized_type[9:]
        if '|null' in normalized_type:
            return normalized_type.replace('|null', '')
        return None
    
    def add_custom_mapping(self, python_type: str, ts_type: str):
        """添加自定义类型映射"""
        self.mapping[python_type] = ts_type
    
    def get_mapping_table(self) -> List[TypeMappingRule]:
        """获取完整映射表"""
        rules = []
        for py_type, ts_type in self.mapping.items():
            rules.append(TypeMappingRule(
                python_type=py_type,
                typescript_type=ts_type,
                notes=""
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


def get_type_mismatch_reason(python_type: str, ts_type: str) -> str:
    """便捷函数：获取类型不匹配原因"""
    mapper = TypeMapper()
    return mapper.get_type_mismatch_reason(python_type, ts_type)
