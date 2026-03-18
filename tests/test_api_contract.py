"""
BMAD-Fullstack API Contract Tests
Phase 2 MVP - 单元测试
"""

import unittest
import sys
import os

# 添加 lib 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

# 使用绝对导入
import api_contract.types as types_module
import api_contract.type_mapper as type_mapper_module
import parsers.pydantic_parser as pydantic_parser_module
import generators.typescript_generator as ts_generator_module

# 获取类
NormalizedSchema = types_module.NormalizedSchema
FieldInfo = types_module.FieldInfo
FieldType = types_module.FieldType
Severity = types_module.Severity
TypeMapper = type_mapper_module.TypeMapper
check_type_compatibility = type_mapper_module.check_type_compatibility
extract_schemas_from_code = pydantic_parser_module.extract_schemas_from_code
TypeScriptGenerator = ts_generator_module.TypeScriptGenerator


class TestTypeMapper(unittest.TestCase):
    """测试类型映射器"""
    
    def setUp(self):
        self.mapper = TypeMapper()
    
    def test_basic_types(self):
        """测试基础类型映射"""
        self.assertEqual(self.mapper.python_to_typescript("str"), "string")
        self.assertEqual(self.mapper.python_to_typescript("int"), "number")
        self.assertEqual(self.mapper.python_to_typescript("float"), "number")
        self.assertEqual(self.mapper.python_to_typescript("bool"), "boolean")
    
    def test_generic_types(self):
        """测试泛型类型映射"""
        self.assertEqual(self.mapper.python_to_typescript("List[str]"), "string[]")
        self.assertEqual(self.mapper.python_to_typescript("Optional[int]"), "number | undefined")
        self.assertEqual(self.mapper.python_to_typescript("Dict[str, int]"), "Record<string, number>")


class TestPydanticParser(unittest.TestCase):
    """测试 Pydantic 解析器"""
    
    def test_parse_simple_model(self):
        """测试解析简单 Model"""
        code = '''
from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    """用户创建请求"""
    username: str
    email: str
    age: Optional[int] = None
'''
        
        schemas = extract_schemas_from_code(code)
        self.assertEqual(len(schemas), 1)
        
        schema = schemas[0]
        self.assertEqual(schema.name, "UserCreate")
        self.assertEqual(len(schema.fields), 3)
        self.assertIn("username", schema.fields)


class TestTypeScriptGenerator(unittest.TestCase):
    """测试 TypeScript 生成器"""
    
    def test_generate_interface(self):
        """测试生成 Interface"""
        schema = NormalizedSchema(name="User", source_language="python")
        schema.add_field(FieldInfo(name="username", field_type=FieldType.STRING,
                                  original_type="str", required=True))
        schema.add_field(FieldInfo(name="age", field_type=FieldType.INTEGER,
                                  original_type="int", required=False))
        
        generator = TypeScriptGenerator(naming_convention="camelCase")
        ts_code = generator.generate_from_schema(schema)
        
        self.assertIn("export interface User", ts_code)
        self.assertIn("username: string;", ts_code)


if __name__ == '__main__':
    unittest.main(verbosity=2)
