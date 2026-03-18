"""
BMAD-EVO API Contract Checker
Phase 2 MVP - 契约检查器核心
"""

import re
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher

from api_contract.types import (
    NormalizedSchema, FieldInfo, FieldType, ContractIssue, 
    ContractReport, Severity, ProjectConfig
)
from api_contract.type_mapper import TypeMapper


class NamingConverter:
    """命名转换工具"""
    
    @staticmethod
    def snake_to_camel(name: str) -> str:
        """snake_case → camelCase"""
        parts = name.split('_')
        return parts[0] + ''.join(word.capitalize() for word in parts[1:])
    
    @staticmethod
    def camel_to_snake(name: str) -> str:
        """camelCase → snake_case"""
        import re as re_module
        s1 = re_module.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re_module.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    @staticmethod
    def normalize_name(name: str, target_convention: str = 'camelCase') -> str:
        """
        标准化字段名称
        
        Args:
            name: 原始名称
            target_convention: 目标命名约定 (camelCase | snake_case)
            
        Returns:
            标准化后的名称
        """
        if target_convention == 'camelCase':
            if '_' in name:
                return NamingConverter.snake_to_camel(name)
            return name
        elif target_convention == 'snake_case':
            if '_' not in name and any(c.isupper() for c in name):
                return NamingConverter.camel_to_snake(name)
            return name
        else:
            raise ValueError(f"不支持的命名约定: {target_convention}")


class ApiContractChecker:
    """
    API 契约一致性检查器
    
    使用方式:
        checker = ApiContractChecker(config)
        report = checker.check_contract(
            backend_schemas={'UserCreate': schema1},
            frontend_schemas={'UserCreate': schema2}
        )
    """
    
    def __init__(self, config: Optional[ProjectConfig] = None):
        """
        初始化检查器
        
        Args:
            config: 项目配置
        """
        self.config = config or ProjectConfig()
        self.type_mapper = TypeMapper()
        self.naming_converter = NamingConverter()
        self.issues: List[ContractIssue] = []
    
    def check_contract(
        self, 
        backend_schemas: Dict[str, NormalizedSchema],
        frontend_schemas: Dict[str, NormalizedSchema]
    ) -> ContractReport:
        """
        检查前后端契约一致性
        
        Args:
            backend_schemas: 后端 Schema 字典 {name: schema}
            frontend_schemas: 前端 Schema 字典 {name: schema}
            
        Returns:
            ContractReport 检查报告
        """
        self.issues = []
        
        # 1. 查找匹配的 Schema
        matched_pairs = self._find_matching_schemas(backend_schemas, frontend_schemas)
        
        # 2. 检查每一对匹配的 Schema
        for backend_name, frontend_name in matched_pairs:
            backend_schema = backend_schemas[backend_name]
            frontend_schema = frontend_schemas[frontend_name]
            
            self._check_schema_pair(backend_schema, frontend_schema)
        
        # 3. 检查缺失的 Schema
        self._check_missing_schemas(backend_schemas, frontend_schemas, matched_pairs)
        
        # 4. 生成报告
        return self._generate_report(backend_schemas, frontend_schemas, matched_pairs)
    
    def _find_matching_schemas(
        self,
        backend_schemas: Dict[str, NormalizedSchema],
        frontend_schemas: Dict[str, NormalizedSchema]
    ) -> List[Tuple[str, str]]:
        """
        查找匹配的前后 Schema
        
        匹配规则：
        1. 名称完全匹配
        2. 名称相似度 >= 0.8（如：UserCreate ↔ IUserCreate）
        """
        matched = []
        backend_used = set()
        frontend_used = set()
        
        # 首先尝试完全匹配
        for b_name in backend_schemas:
            if b_name in frontend_schemas:
                matched.append((b_name, b_name))
                backend_used.add(b_name)
                frontend_used.add(b_name)
        
        # 然后尝试相似匹配
        for b_name in backend_schemas:
            if b_name in backend_used:
                continue
            
            best_match = None
            best_score = 0.0
            
            for f_name in frontend_schemas:
                if f_name in frontend_used:
                    continue
                
                score = self._calculate_similarity(b_name, f_name)
                if score > best_score and score >= 0.8:
                    best_score = score
                    best_match = f_name
            
            if best_match:
                matched.append((b_name, best_match))
                backend_used.add(b_name)
                frontend_used.add(best_match)
        
        return matched
    
    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """计算两个字符串的相似度"""
        # 移除常见前缀/后缀后比较
        prefixes = ['I', 'T', 'Create', 'Update', 'Response', 'Request']
        s1_clean = s1
        s2_clean = s2
        
        for prefix in prefixes:
            if s1_clean.startswith(prefix):
                s1_clean = s1_clean[len(prefix):]
            if s2_clean.startswith(prefix):
                s2_clean = s2_clean[len(prefix):]
        
        return SequenceMatcher(None, s1_clean, s2_clean).ratio()
    
    def _check_schema_pair(self, backend: NormalizedSchema, frontend: NormalizedSchema):
        """检查一对匹配的 Schema"""
        # 1. 字段名称检查
        if self.config.check_field_names:
            self._check_field_names(backend, frontend)
        
        # 2. 字段类型检查
        if self.config.check_field_types:
            self._check_field_types(backend, frontend)
        
        # 3. 必填/可选检查
        if self.config.check_required:
            self._check_required_fields(backend, frontend)
    
    def _check_field_names(self, backend: NormalizedSchema, frontend: NormalizedSchema):
        """检查字段名称一致性"""
        backend_fields = set(backend.get_field_names())
        frontend_fields = set(frontend.get_field_names())
        
        # 后端有但前端没有的字段
        missing_in_frontend = backend_fields - frontend_fields
        for field_name in missing_in_frontend:
            # 检查是否是因为命名约定不同导致的
            normalized_backend = self.naming_converter.normalize_name(
                field_name, self.config.naming_convention
            )
            
            # 在前端查找匹配的名称
            matched = False
            for f_name in frontend_fields:
                normalized_frontend = self.naming_converter.normalize_name(
                    f_name, self.config.naming_convention
                )
                if normalized_backend == normalized_frontend:
                    matched = True
                    break
            
            if not matched:
                field = backend.get_field(field_name)
                self.issues.append(ContractIssue(
                    severity=Severity.CRITICAL,
                    rule="field_name_match",
                    message=f"字段 '{field_name}' 在后端定义但前端缺失",
                    schema_name=backend.name,
                    field_name=field_name,
                    backend_value=field_name,
                    suggestion=f"在前端 {frontend.name} 接口中添加字段: {field_name}",
                    backend_file=backend.source_file,
                    backend_line=field.source_line if field else 0
                ))
        
        # 前端有但后端没有的字段
        missing_in_backend = frontend_fields - backend_fields
        for field_name in missing_in_backend:
            # 同样检查命名约定
            normalized_frontend = self.naming_converter.normalize_name(
                field_name, self.config.naming_convention
            )
            
            matched = False
            for b_name in backend_fields:
                normalized_backend = self.naming_converter.normalize_name(
                    b_name, self.config.naming_convention
                )
                if normalized_backend == normalized_frontend:
                    matched = True
                    break
            
            if not matched:
                field = frontend.get_field(field_name)
                self.issues.append(ContractIssue(
                    severity=Severity.HIGH,
                    rule="field_name_match",
                    message=f"字段 '{field_name}' 在前端定义但后端缺失",
                    schema_name=frontend.name,
                    field_name=field_name,
                    frontend_value=field_name,
                    suggestion=f"在后端 {backend.name} 模型中添加字段: {field_name}，或从前端移除",
                    frontend_file=frontend.source_file,
                    frontend_line=field.source_line if field else 0
                ))
    
    def _check_field_types(self, backend: NormalizedSchema, frontend: NormalizedSchema):
        """检查字段类型一致性"""
        # 找到共同字段（考虑命名转换）
        common_fields = []
        
        for b_name, b_field in backend.fields.items():
            normalized_b = self.naming_converter.normalize_name(
                b_name, self.config.naming_convention
            )
            
            for f_name, f_field in frontend.fields.items():
                normalized_f = self.naming_converter.normalize_name(
                    f_name, self.config.naming_convention
                )
                
                if normalized_b == normalized_f:
                    common_fields.append((b_name, f_name))
                    break
        
        # 检查类型
        for b_name, f_name in common_fields:
            backend_field = backend.get_field(b_name)
            frontend_field = frontend.get_field(f_name)
            
            # 获取原始类型字符串
            backend_type = backend_field.original_type or str(backend_field.field_type.value)
            frontend_type = frontend_field.original_type or str(frontend_field.field_type.value)
            
            # 检查类型兼容性
            if not self.type_mapper.are_types_compatible(backend_type, frontend_type):
                severity = Severity.CRITICAL if self.config.strict_mode else Severity.HIGH
                
                self.issues.append(ContractIssue(
                    severity=severity,
                    rule="field_type_match",
                    message=f"字段 '{b_name}' (前端: '{f_name}') 类型不匹配",
                    schema_name=backend.name,
                    field_name=f"{b_name} / {f_name}",
                    detail=self.type_mapper.get_type_mismatch_reason(backend_type, frontend_type),
                    backend_value=backend_type,
                    frontend_value=frontend_type,
                    suggestion=f"统一类型: 后端 '{backend_type}' ↔ 前端 '{frontend_type}'",
                    backend_file=backend.source_file,
                    backend_line=backend_field.source_line,
                    frontend_file=frontend.source_file,
                    frontend_line=frontend_field.source_line
                ))
    
    def _check_required_fields(self, backend: NormalizedSchema, frontend: NormalizedSchema):
        """检查必填/可选一致性"""
        # 同样找到共同字段
        common_fields = []
        
        for b_name, b_field in backend.fields.items():
            normalized_b = self.naming_converter.normalize_name(
                b_name, self.config.naming_convention
            )
            
            for f_name, f_field in frontend.fields.items():
                normalized_f = self.naming_converter.normalize_name(
                    f_name, self.config.naming_convention
                )
                
                if normalized_b == normalized_f:
                    common_fields.append((b_name, f_name))
                    break
        
        # 检查必填状态
        for b_name, f_name in common_fields:
            backend_field = backend.get_field(b_name)
            frontend_field = frontend.get_field(f_name)
            
            if backend_field.required != frontend_field.required:
                if backend_field.required and not frontend_field.required:
                    # 后端必填但前端可选
                    self.issues.append(ContractIssue(
                        severity=Severity.HIGH,
                        rule="required_match",
                        message=f"字段 '{b_name}' 在后端必填但在前端可选",
                        schema_name=backend.name,
                        field_name=b_name,
                        detail=f"后端定义为必填, 前端定义为可选",
                        backend_value="required",
                        frontend_value="optional",
                        suggestion="统一必填/可选状态，建议后端使用 Optional[T] 或前端改为必填",
                        backend_file=backend.source_file,
                        backend_line=backend_field.source_line,
                        frontend_file=frontend.source_file,
                        frontend_line=frontend_field.source_line
                    ))
                else:
                    # 后端可选但前端必填（较宽松，警告级别）
                    self.issues.append(ContractIssue(
                        severity=Severity.LOW,
                        rule="required_match",
                        message=f"字段 '{b_name}' 在后端可选但在前端必填",
                        schema_name=backend.name,
                        field_name=b_name,
                        detail=f"后端定义为可选, 前端定义为必填",
                        backend_value="optional",
                        frontend_value="required",
                        suggestion="统一必填/可选状态",
                        backend_file=backend.source_file,
                        backend_line=backend_field.source_line,
                        frontend_file=frontend.source_file,
                        frontend_line=frontend_field.source_line
                    ))
    
    def _check_missing_schemas(
        self,
        backend_schemas: Dict[str, NormalizedSchema],
        frontend_schemas: Dict[str, NormalizedSchema],
        matched_pairs: List[Tuple[str, str]]
    ):
        """检查缺失的 Schema"""
        backend_matched = {pair[0] for pair in matched_pairs}
        frontend_matched = {pair[1] for pair in matched_pairs}
        
        # 后端有但前端无对应 Schema
        for name in backend_schemas:
            if name not in backend_matched:
                # 检查是否在忽略列表
                if name not in self.config.ignored_schemas:
                    self.issues.append(ContractIssue(
                        severity=Severity.MEDIUM,
                        rule="schema_match",
                        message=f"Schema '{name}' 在后端定义但前端无对应类型",
                        schema_name=name,
                        suggestion=f"在前端创建对应的 Interface/Type: {name}",
                        backend_file=backend_schemas[name].source_file
                    ))
        
        # 前端有但后端无对应 Schema
        for name in frontend_schemas:
            if name not in frontend_matched:
                if name not in self.config.ignored_schemas:
                    self.issues.append(ContractIssue(
                        severity=Severity.LOW,
                        rule="schema_match",
                        message=f"类型 '{name}' 在前端定义但后端无对应 Schema",
                        schema_name=name,
                        suggestion=f"在后端创建对应的 Pydantic Model，或从前端移除",
                        frontend_file=frontend_schemas[name].source_file
                    ))
    
    def _generate_report(
        self,
        backend_schemas: Dict[str, NormalizedSchema],
        frontend_schemas: Dict[str, NormalizedSchema],
        matched_pairs: List[Tuple[str, str]]
    ) -> ContractReport:
        """生成检查报告"""
        # 计算分数
        score = self._calculate_score(backend_schemas, frontend_schemas, matched_pairs)
        
        # 生成摘要
        summary = self._generate_summary(backend_schemas, frontend_schemas, matched_pairs)
        
        # 生成建议
        recommendations = self._generate_recommendations()
        
        # 确定是否通过
        passed = score >= self.config.min_score and not any(
            i.severity == Severity.CRITICAL for i in self.issues
        )
        
        if self.config.block_on_high and any(
            i.severity == Severity.HIGH for i in self.issues
        ):
            passed = False
        
        return ContractReport(
            passed=passed,
            score=score,
            issues=self.issues,
            summary=summary,
            recommendations=recommendations,
            backend_schemas_count=len(backend_schemas),
            frontend_schemas_count=len(frontend_schemas),
            matched_schemas=len(matched_pairs)
        )
    
    def _calculate_score(
        self,
        backend_schemas: Dict[str, NormalizedSchema],
        frontend_schemas: Dict[str, NormalizedSchema],
        matched_pairs: List[Tuple[str, str]]
    ) -> float:
        """计算契约得分"""
        total_checks = 0
        passed_checks = 0
        
        # Schema 匹配得分
        total_schemas = len(backend_schemas) + len(frontend_schemas)
        matched_schemas = len(matched_pairs) * 2
        total_checks += total_schemas
        passed_checks += matched_schemas
        
        # 字段检查得分
        for b_name, f_name in matched_pairs:
            backend = backend_schemas[b_name]
            frontend = frontend_schemas[f_name]
            
            backend_fields = set(backend.get_field_names())
            frontend_fields = set(frontend.get_field_names())
            
            total_checks += len(backend_fields) + len(frontend_fields)
            passed_checks += len(backend_fields & frontend_fields) * 2
        
        # 扣分计算
        severity_penalty = {
            Severity.CRITICAL: 15,
            Severity.HIGH: 8,
            Severity.MEDIUM: 3,
            Severity.LOW: 1
        }
        
        penalty = sum(severity_penalty.get(i.severity, 0) for i in self.issues)
        
        # 计算最终分数
        if total_checks == 0:
            return 100.0
        
        base_score = (passed_checks / total_checks) * 100
        final_score = max(0, base_score - penalty)
        
        return round(final_score, 1)
    
    def _generate_summary(
        self,
        backend_schemas: Dict[str, NormalizedSchema],
        frontend_schemas: Dict[str, NormalizedSchema],
        matched_pairs: List[Tuple[str, str]]
    ) -> str:
        """生成报告摘要"""
        lines = [
            f"API 契约检查完成",
            f"",
            f"后端 Schema: {len(backend_schemas)} 个",
            f"前端类型: {len(frontend_schemas)} 个",
            f"匹配对: {len(matched_pairs)} 对",
            f"",
            f"发现问题: {len(self.issues)} 个",
            f"  - CRITICAL: {len([i for i in self.issues if i.severity == Severity.CRITICAL])}",
            f"  - HIGH: {len([i for i in self.issues if i.severity == Severity.HIGH])}",
            f"  - MEDIUM: {len([i for i in self.issues if i.severity == Severity.MEDIUM])}",
            f"  - LOW: {len([i for i in self.issues if i.severity == Severity.LOW])}",
        ]
        
        return "\n".join(lines)
    
    def _generate_recommendations(self) -> List[str]:
        """生成建议"""
        recommendations = []
        
        critical_count = len([i for i in self.issues if i.severity == Severity.CRITICAL])
        high_count = len([i for i in self.issues if i.severity == Severity.HIGH])
        
        if critical_count > 0:
            recommendations.append(f"立即修复 {critical_count} 个 CRITICAL 问题，否则会阻断流程")
        
        if high_count > 0:
            recommendations.append(f"建议修复 {high_count} 个 HIGH 优先级问题")
        
        if self.config.naming_convention == 'camelCase':
            recommendations.append("建议统一使用 camelCase 命名约定")
        
        return recommendations
