"""
Pydantic Parser - Python/Pydantic Schema 提取器
从 Python 代码中提取 Pydantic Model 定义
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass

from ..api_contract.types import (
    NormalizedSchema, FieldInfo, FieldType, ProjectConfig
)


class PydanticModelVisitor(ast.NodeVisitor):
    """AST 访问者 - 提取 Pydantic Model"""
    
    def __init__(self, source_code: str, filename: str = "<unknown>"):
        self.source_code = source_code
        self.filename = filename
        self.schemas: List[NormalizedSchema] = []
        self.current_schema: Optional[NormalizedSchema] = None
        self.lines = source_code.splitlines()
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """访问类定义，检查是否是 Pydantic Model"""
        # 检查是否继承自 BaseModel
        is_pydantic_model = False
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == 'BaseModel':
                is_pydantic_model = True
            elif isinstance(base, ast.Attribute) and base.attr == 'BaseModel':
                is_pydantic_model = True
            elif isinstance(base, ast.Subscript):
                # 处理 Generic[T] 情况
                if isinstance(base.value, ast.Name) and base.value.id == 'BaseModel':
                    is_pydantic_model = True
        
        if is_pydantic_model:
            schema = NormalizedSchema(
                name=node.name,
                source_file=self.filename,
                source_language="python"
            )
            
            # 提取类文档字符串
            docstring = ast.get_docstring(node)
            if docstring:
                schema.description = docstring.strip()
            
            self.current_schema = schema
            
            # 访问类体中的所有赋值语句
            for item in node.body:
                if isinstance(item, (ast.AnnAssign, ast.Assign)):
                    self._extract_field(item)
            
            self.schemas.append(schema)
            self.current_schema = None
        
        # 继续访问嵌套类
        self.generic_visit(node)
    
    def _extract_field(self, node: Union[ast.AnnAssign, ast.Assign]):
        """从赋值语句提取字段信息"""
        if self.current_schema is None:
            return
        
        field_info = FieldInfo(
            source_file=self.filename,
            source_language="python",
            source_line=getattr(node, 'lineno', 0)
        )
        
        if isinstance(node, ast.AnnAssign):
            # 类型注解赋值（如：name: str）
            if isinstance(node.target, ast.Name):
                field_info.name = node.target.id
                field_info.field_type = self._parse_type_annotation(node.annotation)
                field_info.original_type = self._get_type_string(node.annotation)
                
                # 检查是否有默认值
                if node.value:
                    field_info.required = False
                    field_info.default = self._extract_default_value(node.value)
                    
                    # 检查是否是 Field(...) 定义
                    if isinstance(node.value, ast.Call):
                        field_info = self._parse_field_call(node.value, field_info)
        
        elif isinstance(node, ast.Assign):
            # 普通赋值（如：name = Field(...)）
            for target in node.targets:
                if isinstance(target, ast.Name):
                    field_info.name = target.id
                    
                    if isinstance(node.value, ast.Call):
                        field_info = self._parse_field_call(node.value, field_info)
        
        if field_info.name:
            self.current_schema.add_field(field_info)
    
    def _parse_type_annotation(self, node: ast.AST) -> FieldType:
        """解析类型注解为 FieldType"""
        type_str = self._get_type_string(node)
        return self._map_python_type_to_field_type(type_str)
    
    def _get_type_string(self, node: ast.AST) -> str:
        """从 AST 节点获取类型字符串"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Attribute):
            return f"{self._get_type_string(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            value = self._get_type_string(node.value)
            slice_str = self._get_type_string(node.slice)
            return f"{value}[{slice_str}]"
        elif isinstance(node, ast.Tuple):
            elements = [self._get_type_string(e) for e in node.elts]
            return ", ".join(elements)
        elif isinstance(node, ast.BinOp):
            # 处理 Union 类型（如：str | int）
            if isinstance(node.op, ast.BitOr):
                left = self._get_type_string(node.left)
                right = self._get_type_string(node.right)
                return f"{left} | {right}"
        elif isinstance(node, ast.Expr):
            return self._get_type_string(node.value)
        
        return str(node)
    
    def _map_python_type_to_field_type(self, type_str: str) -> FieldType:
        """将 Python 类型字符串映射为 FieldType"""
        type_mapping = {
            'str': FieldType.STRING,
            'string': FieldType.STRING,
            'int': FieldType.INTEGER,
            'integer': FieldType.INTEGER,
            'float': FieldType.NUMBER,
            'number': FieldType.NUMBER,
            'bool': FieldType.BOOLEAN,
            'boolean': FieldType.BOOLEAN,
            'list': FieldType.ARRAY,
            'List': FieldType.ARRAY,
            'dict': FieldType.OBJECT,
            'Dict': FieldType.OBJECT,
            'Any': FieldType.ANY,
            'None': FieldType.NULL,
            'NoneType': FieldType.NULL,
            'datetime': FieldType.DATETIME,
            'date': FieldType.DATE,
            'UUID': FieldType.UUID,
            'EmailStr': FieldType.EMAIL,
            'HttpUrl': FieldType.URL,
        }
        
        # 检查是否是数组类型
        if type_str.startswith(('List[', 'list[')):
            return FieldType.ARRAY
        
        # 检查是否是可选类型
        if type_str.startswith('Optional['):
            inner = type_str[9:-1]  # 提取 Optional[...] 内部
            return self._map_python_type_to_field_type(inner)
        
        # 检查是否是联合类型
        if '|' in type_str or 'Union[' in type_str:
            return FieldType.UNION
        
        return type_mapping.get(type_str, FieldType.ANY)
    
    def _parse_field_call(self, node: ast.Call, field_info: FieldInfo) -> FieldInfo:
        """解析 Field(...) 调用"""
        if isinstance(node.func, ast.Name) and node.func.id == 'Field':
            for keyword in node.keywords:
                if keyword.arg == 'description':
                    field_info.description = self._extract_string_value(keyword.value)
                elif keyword.arg == 'default':
                    field_info.default = self._extract_default_value(keyword.value)
                    field_info.required = False
                elif keyword.arg == 'default_factory':
                    field_info.required = False
        
        return field_info
    
    def _extract_default_value(self, node: ast.AST) -> Any:
        """提取默认值"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.NameConstant):
            return node.value
        elif isinstance(node, ast.List):
            return [self._extract_default_value(e) for e in node.elts]
        elif isinstance(node, ast.Dict):
            return {
                self._extract_default_value(k): self._extract_default_value(v)
                for k, v in zip(node.keys, node.values)
            }
        return None
    
    def _extract_string_value(self, node: ast.AST) -> str:
        """提取字符串值"""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        elif isinstance(node, ast.Str):
            return node.s
        return ""


class PydanticSchemaExtractor:
    """Pydantic Schema 提取器"""
    
    def __init__(self, project_config: ProjectConfig):
        self.config = project_config
    
    def extract_from_file(self, file_path: str) -> List[NormalizedSchema]:
        """从单个文件提取 Schema"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            tree = ast.parse(source_code, filename=file_path)
            visitor = PydanticModelVisitor(source_code, file_path)
            visitor.visit(tree)
            
            return visitor.schemas
        except SyntaxError as e:
            print(f"语法错误 in {file_path}: {e}")
            return []
        except Exception as e:
            print(f"解析错误 in {file_path}: {e}")
            return []
    
    def extract_from_directory(self, dir_path: str) -> List[NormalizedSchema]:
        """从目录提取所有 Schema"""
        all_schemas = []
        
        for root, dirs, files in os.walk(dir_path):
            # 跳过忽略目录
            dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', 'venv', 'node_modules')]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    schemas = self.extract_from_file(file_path)
                    all_schemas.extend(schemas)
        
        return all_schemas
    
    def extract_all(self) -> Dict[str, NormalizedSchema]:
        """提取项目中所有 Schema"""
        schema_path = self.config.backend_schema_path
        
        if not schema_path or not os.path.exists(schema_path):
            return {}
        
        all_schemas = []
        
        if os.path.isfile(schema_path):
            all_schemas = self.extract_from_file(schema_path)
        else:
            all_schemas = self.extract_from_directory(schema_path)
        
        # 转换为字典
        return {schema.name: schema for schema in all_schemas}


# 便捷函数
def extract_schemas_from_code(source_code: str, filename: str = "<unknown>") -> List[NormalizedSchema]:
    """从代码字符串提取 Schema"""
    try:
        tree = ast.parse(source_code, filename=filename)
        visitor = PydanticModelVisitor(source_code, filename)
        visitor.visit(tree)
        return visitor.schemas
    except SyntaxError as e:
        print(f"语法错误: {e}")
        return []
