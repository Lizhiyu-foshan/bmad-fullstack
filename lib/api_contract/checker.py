"""
API Contract Checker - 契约检查器核心
对比前后端 Schema，检测不一致
"""

from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher

from ..api_contract.types import (
    NormalizedSchema, FieldInfo, FieldType, ContractIssue, 
    ContractReport, Severity, ProjectConfig
)
from ..api_contract.type_mapper import TypeMapper


class ApiContractChecker:
    """API 契约检查器"""
    
    def __init__(self, project_config: ProjectConfig):
        self.config = project_config
        self.type_mapper = TypeMapper()
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
        2. 名称相似度 > 0.8（如：UserCreate ↔ IUserCreate）
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
            s1_clean = s1_clean.removeprefix(prefix)
            s2_clean = s2_clean.removeprefix(prefix)
        
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
            field = backend.get_field(field_name)
            self.issues.append(ContractIssue(
                severity=Severity.HIGH,
                rule="field_name_match",
                message=f"字段 '{field_name}' 在后端定义但前端缺失",
                schema_name=backend.name,
                field_name=field_name,
                backend_info=field,
                suggestion=f"在前端 {frontend.name} 接口中添加字段: {field_name}"
            ))
        
        # 前端有但后端没有的字段
        missing_in_backend = frontend_fields - backend_fields
        for field_name in missing_in_backend:
            field = frontend.get_field(field_name)
            self.issues.append(ContractIssue(
                severity=Severity.MEDIUM,
                rule="field_name_match",
                message=f"字段 '{field_name}' 在前端定义但后端缺失",
                schema_name=frontend.name,
                field_name=field_name,
                frontend_info=field,
                suggestion=f"在后端 {backend.name} 模型中添加字段: {field_name}，或从前端移除"
            ))
    
    def _check_field_types(self, backend: NormalizedSchema, frontend: NormalizedSchema):
        """检查字段类型一致性"""
        common_fields = set(backend.get_field_names()) & set(frontend.get_field_names())
        
        for field_name in common_fields:
            backend_field = backend.get_field(field_name)
            frontend_field = frontend.get_field(field_name)
            
            # 获取原始类型字符串
            backend_type = backend_field.original_type or str(backend_field.field_type.value)
            frontend_type = frontend_field.original_type or str(frontend_field.field_type.value)
            
            # 检查类型兼容性
            if not self.type_mapper.are_types_compatible(backend_type, frontend_type):
                reason = self.type_mapper.get_type_mismatch_reason(backend_type, frontend_type)
                
                self.issues.append(ContractIssue(
                    severity=Severity.CRITICAL if self.config.type_strictness == "strict" else Severity.HIGH,
                    rule="field_type_match",
                    message=f"字段 '{field_name}' 类型不匹配: {reason}",
                    schema_name=backend.name,
                    field_name=field_name,
                    backend_info=backend_field,
                    frontend_info=frontend_field,
                    suggestion=f"统一类型: 后端 '{backend_type}' ↔ 前端 '{frontend_type}'"
                ))
    
    def _check_required_fields(self, backend: NormalizedSchema, frontend: NormalizedSchema):
        """检查必填/可选一致性"""
        common_fields = set(backend.get_field_names()) & set(frontend.get_field_names())
        
        for field_name in common_fields:
            backend_field = backend.get_field(field_name)
            frontend_field = frontend.get_field(field_name)
            
            # 检查必填状态
            if backend_field.required != frontend_field.required:
                if backend_field.required and not frontend_field.required:
                    # 后端必填但前端可选
                    self.issues.append(ContractIssue(
                        severity=Severity.HIGH,
                        rule="required_consistency",
                        message=f"字段 '{field_name}' 在后端必填但在前端可选",
                        schema_name=backend.name,
                        field_name=field_name,
                        backend_info=backend_field,
                        frontend_info=frontend_field,
                        suggestion="统一必填/可选状态，建议后端 Optional 或前端改为必填"
                    ))
                else:
                    # 后端可选但前端必填（较宽松，警告级别）
                    self.issues.append(ContractIssue(
                        severity=Severity.LOW,
                        rule="required_consistency",
                        message=f"字段 '{field_name}' 在后端可选但在前端必填",
                        schema_name=backend.name,
                        field_name=field_name,
                        backend_info=backend_field,
                        frontend_info=frontend_field,
                        suggestion="统一必填/可选状态"
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
                if name not in self.config.ignore_schemas:
                    self.issues.append(ContractIssue(
                        severity=Severity.MEDIUM,
                        rule="schema_match",
                        message=f"Schema '{name}' 在后端定义但前端无对应类型",
                        schema_name=name,
                        suggestion=f"在前端创建对应的 Interface/Type: {name}"
                    ))
        
        # 前端有但后端无对应 Schema
        for name in frontend_schemas:
            if name not in frontend_matched:
                if name not in self.config.ignore_schemas:
                    self.issues.append(ContractIssue(
                        severity=Severity.LOW,
                        rule="schema_match",
                        message=f"类型 '{name}' 在前端定义但后端无对应 Schema",
                        schema_name=name,
                        suggestion=f"在后端创建对应的 Pydantic Model，或从前端移除"
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
        
        return ContractReport(
            passed=score >= 85 and not any(i.severity == Severity.CRITICAL for i in self.issues),
            score=score,
            issues=self.issues,
            summary=summary,
            total_schemas=len(backend_schemas) + len(frontend_schemas),
            matched_schemas=len(matched_pairs),
            mismatched_schemas=len(backend_schemas) + len(frontend_schemas) - len(matched_pairs) * 2
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
            Severity.CRITICAL: 20,
            Severity.HIGH: 10,
            Severity.MEDIUM: 5,
            Severity.LOW: 2
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
