"""
TypeScript Parser - TypeScript Interface/Type 提取器
使用 TypeScript 编译器 API 提取类型定义

注意：需要安装 TypeScript npm 包
"""

import json
import os
import subprocess
from typing import List, Dict, Optional, Any
from pathlib import Path

from ..api_contract.types import (
    NormalizedSchema, FieldInfo, FieldType, ProjectConfig
)


class TypeScriptSchemaExtractor:
    """TypeScript Schema 提取器"""
    
    def __init__(self, project_config: ProjectConfig):
        self.config = project_config
        self.type_cache: Dict[str, NormalizedSchema] = {}
    
    def _run_typescript_compiler(self, file_path: str) -> Optional[Dict]:
        """
        使用 TypeScript 编译器获取 AST 信息
        
        通过运行 Node.js 脚本来调用 TypeScript API
        """
        # 创建临时 JS 脚本来提取类型信息
        script = f"""
const ts = require('typescript');
const fs = require('fs');

const filePath = '{file_path}';
const sourceCode = fs.readFileSync(filePath, 'utf-8');

const sourceFile = ts.createSourceFile(
    filePath,
    sourceCode,
    ts.ScriptTarget.Latest,
    true
);

const types = [];

function visit(node) {{
    // Interface 声明
    if (ts.isInterfaceDeclaration(node)) {{
        const members = node.members.map(member => {{
            if (ts.isPropertySignature(member)) {{
                return {{
                    name: member.name.getText(sourceFile),
                    type: member.type ? member.type.getText(sourceFile) : 'any',
                    optional: !!member.questionToken
                }};
            }}
            return null;
        }}).filter(m => m !== null);
        
        types.push({{
            kind: 'interface',
            name: node.name.getText(sourceFile),
            members: members
        }});
    }}
    
    // Type 别名
    if (ts.isTypeAliasDeclaration(node)) {{
        types.push({{
            kind: 'type',
            name: node.name.getText(sourceFile),
            type: node.type.getText(sourceFile)
        }});
    }}
}}

ts.forEachChild(sourceFile, visit);

console.log(JSON.stringify(types, null, 2));
"""
        
        try:
            # 写入临时脚本
            temp_script = '/tmp/ts_extract_types.js'
            with open(temp_script, 'w') as f:
                f.write(script)
            
            # 运行 Node.js 脚本
            result = subprocess.run(
                ['node', temp_script],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                print(f"TypeScript 解析错误: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            print("TypeScript 解析超时")
            return None
        except FileNotFoundError:
            print("Node.js 未安装，无法解析 TypeScript")
            return None
        except Exception as e:
            print(f"解析异常: {e}")
            return None
    
    def _parse_type_string(self, type_str: str) -> FieldType:
        """将 TypeScript 类型字符串映射为 FieldType"""
        type_mapping = {
            'string': FieldType.STRING,
            'number': FieldType.NUMBER,
            'boolean': FieldType.BOOLEAN,
            'any': FieldType.ANY,
            'null': FieldType.NULL,
            'undefined': FieldType.NULL,
            'unknown': FieldType.ANY,
            'never': FieldType.ANY,
            'Date': FieldType.DATETIME,
        }
        
        # 检查数组类型
        if type_str.endswith('[]') or type_str.startswith('Array<'):
            return FieldType.ARRAY
        
        # 检查对象类型
        if type_str.startswith('Record<') or type_str == 'object':
            return FieldType.OBJECT
        
        # 检查联合类型
        if '|' in type_str:
            return FieldType.UNION
        
        return type_mapping.get(type_str, FieldType.ANY)
    
    def _convert_to_normalized_schema(self, ts_type: Dict) -> Optional[NormalizedSchema]:
        """将 TypeScript 类型转换为 NormalizedSchema"""
        if ts_type['kind'] != 'interface':
            # 暂时只支持 Interface
            return None
        
        schema = NormalizedSchema(
            name=ts_type['name'],
            source_language="typescript"
        )
        
        for member in ts_type.get('members', []):
            field = FieldInfo(
                name=member['name'],
                field_type=self._parse_type_string(member['type']),
                required=not member.get('optional', False),
                original_type=member['type'],
                source_language="typescript"
            )
            
            # 处理可选类型（如：string | undefined）
            if '| undefined' in member['type'] or '| null' in member['type']:
                field.required = False
                field.nullable = True
            
            schema.add_field(field)
        
        return schema
    
    def extract_from_file(self, file_path: str) -> List[NormalizedSchema]:
        """从单个 TypeScript 文件提取 Schema"""
        if not file_path.endswith(('.ts', '.tsx')):
            return []
        
        ts_types = self._run_typescript_compiler(file_path)
        if not ts_types:
            return []
        
        schemas = []
        for ts_type in ts_types:
            schema = self._convert_to_normalized_schema(ts_type)
            if schema:
                schema.source_file = file_path
                schemas.append(schema)
        
        return schemas
    
    def extract_from_directory(self, dir_path: str) -> List[NormalizedSchema]:
        """从目录提取所有 TypeScript 类型"""
        all_schemas = []
        
        for root, dirs, files in os.walk(dir_path):
            # 跳过忽略目录
            dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', 'dist', 'build')]
            
            for file in files:
                if file.endswith(('.ts', '.tsx')) and not file.endswith('.d.ts'):
                    file_path = os.path.join(root, file)
                    schemas = self.extract_from_file(file_path)
                    all_schemas.extend(schemas)
        
        return all_schemas
    
    def extract_all(self) -> Dict[str, NormalizedSchema]:
        """提取项目中所有 TypeScript Schema"""
        type_path = self.config.frontend_type_path
        
        if not type_path or not os.path.exists(type_path):
            return {}
        
        all_schemas = []
        
        if os.path.isfile(type_path):
            all_schemas = self.extract_from_file(type_path)
        else:
            all_schemas = self.extract_from_directory(type_path)
        
        return {schema.name: schema for schema in all_schemas}


class SimpleTypeScriptParser:
    """
    简化版 TypeScript 解析器（正则基础）
    
    用于在无法安装 Node.js/TypeScript 时的降级方案
    """
    
    def __init__(self):
        self.interface_pattern = re.compile(
            r'interface\s+(\w+)\s*\{([^}]+)\}',
            re.MULTILINE | re.DOTALL
        )
        self.property_pattern = re.compile(
            r'(\w+)\??\s*:\s*([^;\n]+)',
            re.MULTILINE
        )
    
    def parse_interface(self, content: str) -> List[NormalizedSchema]:
        """使用正则解析 Interface"""
        schemas = []
        
        for match in self.interface_pattern.finditer(content):
            name = match.group(1)
            body = match.group(2)
            
            schema = NormalizedSchema(name=name, source_language="typescript")
            
            for prop_match in self.property_pattern.finditer(body):
                prop_name = prop_match.group(1)
                prop_type = prop_match.group(2).strip()
                
                field = FieldInfo(
                    name=prop_name,
                    field_type=FieldType.ANY,  # 简化处理
                    original_type=prop_type,
                    required='?' not in prop_match.group(0),
                    source_language="typescript"
                )
                
                schema.add_field(field)
            
            schemas.append(schema)
        
        return schemas


# 导入 re 用于简化版解析器
import re
