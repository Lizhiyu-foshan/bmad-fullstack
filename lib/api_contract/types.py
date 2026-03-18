"""
BMAD-Fullstack API Contract Types
核心数据类型定义 - 统一前后端 Schema 表示
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class Severity(str, Enum):
    """问题严重级别"""
    CRITICAL = "CRITICAL"  # 必须修复，阻断流程
    HIGH = "HIGH"          # 应该修复，影响功能
    MEDIUM = "MEDIUM"      # 建议修复，影响体验
    LOW = "LOW"            # 可选修复，优化项


class FieldType(str, Enum):
    """统一字段类型（跨语言）"""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    ENUM = "enum"
    ANY = "any"
    NULL = "null"
    DATE = "date"
    DATETIME = "datetime"
    UUID = "uuid"
    EMAIL = "email"
    URL = "url"


@dataclass
class FieldInfo:
    """字段信息（语言无关的统一表示）"""
    name: str
    field_type: FieldType
    required: bool = True
    nullable: bool = False
    default: Any = None
    description: str = ""
    
    # 复杂类型
    enum_values: Optional[List[Any]] = None
    nested_schema: Optional['NormalizedSchema'] = None
    array_item_type: Optional['FieldInfo'] = None
    generic_params: Optional[List['FieldInfo']] = None
    
    # 来源信息
    source_file: str = ""
    source_line: int = 0
    source_language: str = ""  # "python" or "typescript"
    
    # 原始类型（用于调试）
    original_type: str = ""  # 原始类型字符串


@dataclass
class NormalizedSchema:
    """标准化的 Schema 表示（消除语言差异）"""
    name: str
    fields: Dict[str, FieldInfo] = field(default_factory=dict)
    description: str = ""
    
    # 来源信息
    source_file: str = ""
    source_language: str = ""  # "python" or "typescript"
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_field(self, name: str) -> Optional[FieldInfo]:
        """获取字段信息"""
        return self.fields.get(name)
    
    def add_field(self, field_info: FieldInfo):
        """添加字段"""
        self.fields[field_info.name] = field_info
    
    def get_field_names(self) -> List[str]:
        """获取所有字段名"""
        return list(self.fields.keys())


@dataclass
class ContractIssue:
    """契约检查问题"""
    severity: Severity
    rule: str  # 违反的规则名称
    message: str  # 问题描述
    
    # 定位信息
    schema_name: str
    field_name: Optional[str] = None
    
    # 上下文
    backend_info: Optional[FieldInfo] = None
    frontend_info: Optional[FieldInfo] = None
    
    # 修复建议
    suggestion: str = ""
    fix_example: Optional[str] = None


@dataclass
class ContractReport:
    """契约检查报告"""
    passed: bool
    score: float  # 0-100
    issues: List[ContractIssue] = field(default_factory=list)
    summary: str = ""
    
    # 统计
    total_schemas: int = 0
    matched_schemas: int = 0
    mismatched_schemas: int = 0
    
    # 时间戳
    timestamp: str = field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())
    
    def get_critical_issues(self) -> List[ContractIssue]:
        """获取关键问题"""
        return [i for i in self.issues if i.severity == Severity.CRITICAL]
    
    def get_high_issues(self) -> List[ContractIssue]:
        """获取高优先级问题"""
        return [i for i in self.issues if i.severity == Severity.HIGH]
    
    def get_issues_by_schema(self, schema_name: str) -> List[ContractIssue]:
        """获取特定 Schema 的问题"""
        return [i for i in self.issues if i.schema_name == schema_name]


@dataclass
class ProjectConfig:
    """项目配置"""
    project_name: str
    project_type: str = "fullstack"
    
    # 后端配置
    backend_framework: str = "fastapi"  # fastapi, flask, django
    backend_schema_path: str = ""
    backend_main_file: str = ""
    
    # 前端配置
    frontend_framework: str = "react"  # react, vue, nextjs
    frontend_type_path: str = ""
    frontend_api_client_path: str = ""
    
    # 契约检查配置
    check_field_names: bool = True
    check_field_types: bool = True
    check_required: bool = True
    check_enums: bool = True
    type_strictness: str = "strict"  # strict | loose
    
    # 忽略规则
    ignore_patterns: List[str] = field(default_factory=list)
    ignore_schemas: List[str] = field(default_factory=list)


@dataclass
class TypeMappingRule:
    """类型映射规则"""
    python_type: str
    typescript_type: str
    is_compatible: bool = True
    notes: str = ""


# 默认类型映射表
DEFAULT_TYPE_MAPPING: Dict[str, str] = {
    # 基础类型
    'str': 'string',
    'int': 'number',
    'float': 'number',
    'bool': 'boolean',
    'None': 'null',
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
    'datetime': 'string',  # ISO8601
    'date': 'string',
    'UUID': 'string',
    'EmailStr': 'string',
    'HttpUrl': 'string',
    'Path': 'string',
    
    # Pydantic 特殊类型
    'Optional': 'optional',
    'Union': 'union',
    'Literal': 'enum',
}

# TypeScript → Python 反向映射
REVERSE_TYPE_MAPPING: Dict[str, str] = {
    'string': 'str',
    'number': 'float',  # 默认浮点数
    'boolean': 'bool',
    'null': 'None',
    'any': 'Any',
    'array': 'List',
    'object': 'Dict',
    'undefined': 'Optional',
}
