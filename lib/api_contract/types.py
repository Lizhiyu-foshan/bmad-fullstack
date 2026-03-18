"""
BMAD-EVO API Contract Types
Phase 2 MVP - 核心数据类型定义
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class Severity(str, Enum):
    """问题严重级别"""
    CRITICAL = "CRITICAL"  # 必须修复，阻断流程
    HIGH = "HIGH"          # 应该修复
    MEDIUM = "MEDIUM"      # 建议修复
    LOW = "LOW"            # 可选优化


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
    OPTIONAL = "optional"
    UNION = "union"


@dataclass
class FieldInfo:
    """字段信息（统一前后端表示）"""
    name: str
    field_type: FieldType
    original_type: str = ""  # 原始类型字符串
    required: bool = True
    nullable: bool = False
    default: Any = None
    description: str = ""
    enum_values: Optional[List[Any]] = None
    
    # 来源信息
    source_file: str = ""
    source_line: int = 0
    source_language: str = ""  # "python" or "typescript"
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.original_type:
            self.original_type = self.field_type.value


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
    
    def has_field(self, name: str) -> bool:
        """检查是否存在字段"""
        return name in self.fields


@dataclass
class ContractIssue:
    """契约检查问题"""
    severity: Severity
    rule: str  # 违反的规则名称
    message: str  # 问题描述
    
    # 定位信息
    schema_name: str
    field_name: Optional[str] = None
    
    # 详细信息
    detail: str = ""
    backend_value: str = ""  # 后端的定义
    frontend_value: str = ""  # 前端的定义
    
    # 修复建议
    suggestion: str = ""
    
    # 位置信息
    backend_file: str = ""
    backend_line: int = 0
    frontend_file: str = ""
    frontend_line: int = 0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'severity': self.severity.value,
            'rule': self.rule,
            'message': self.message,
            'schema_name': self.schema_name,
            'field_name': self.field_name,
            'detail': self.detail,
            'backend_value': self.backend_value,
            'frontend_value': self.frontend_value,
            'suggestion': self.suggestion,
        }


@dataclass
class ContractReport:
    """契约检查报告"""
    passed: bool
    score: float  # 0-100
    total_checks: int = 0
    passed_checks: int = 0
    issues: List[ContractIssue] = field(default_factory=list)
    
    # 统计信息
    backend_schemas_count: int = 0
    frontend_schemas_count: int = 0
    matched_schemas: int = 0
    fields_checked: int = 0
    
    # 总结
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    
    # 时间戳
    timestamp: str = field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())
    
    def has_critical_issues(self) -> bool:
        """是否有严重问题"""
        return any(i.severity == Severity.CRITICAL for i in self.issues)
    
    def has_blocking_issues(self) -> bool:
        """是否有阻断流程的问题"""
        return self.has_critical_issues() or \
               any(i.severity == Severity.HIGH for i in self.issues)
    
    def get_issues_by_severity(self, severity: Severity) -> List[ContractIssue]:
        """按严重级别获取问题"""
        return [i for i in self.issues if i.severity == severity]
    
    def get_issues_by_schema(self, schema_name: str) -> List[ContractIssue]:
        """获取特定 Schema 的问题"""
        return [i for i in self.issues if i.schema_name == schema_name]


@dataclass
class TypeMappingRule:
    """类型映射规则"""
    python_type: str
    typescript_type: str
    notes: str = ""


@dataclass
class ProjectConfig:
    """项目配置"""
    project_name: str = ""
    naming_convention: str = "camelCase"  # camelCase | snake_case
    strict_mode: bool = False
    
    # 后端配置
    backend_schema_path: str = ""
    backend_framework: str = "fastapi"  # fastapi, flask, django
    
    # 前端配置
    frontend_schema_path: str = ""
    frontend_framework: str = "react"  # react, vue, nextjs
    
    # 检查配置
    check_field_names: bool = True
    check_field_types: bool = True
    check_required: bool = True
    check_enums: bool = True
    
    # 忽略配置
    ignored_fields: List[str] = field(default_factory=list)
    ignored_schemas: List[str] = field(default_factory=list)
    
    # 阈值
    min_score: float = 85.0
    block_on_critical: bool = True
    block_on_high: bool = False
    
    # 报告配置
    report_format: str = "markdown"  # markdown, json, html
    include_suggestions: bool = True
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.ignored_fields:
            self.ignored_fields = ['createdAt', 'updatedAt', '__typename']
