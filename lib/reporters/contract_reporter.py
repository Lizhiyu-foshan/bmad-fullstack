"""
BMAD-EVO Contract Reporter
Phase 2 MVP - 契约检查报告生成器
"""

import json
from typing import List, Dict
from datetime import datetime

from api_contract.types import ContractReport, ContractIssue, Severity


class ContractReporter:
    """契约检查报告生成器"""
    
    def __init__(self, report: ContractReport):
        self.report = report
    
    def to_markdown(self, language: str = "zh") -> str:
        """
        生成 Markdown 格式报告
        
        Args:
            language: 语言 ("zh" 中文, "en" 英文)
        """
        if language == "zh":
            return self._to_markdown_zh()
        else:
            return self._to_markdown_en()
    
    def _to_markdown_zh(self) -> str:
        """生成中文 Markdown 报告"""
        lines = [
            "# API 契约检查报告",
            "",
            f"**检查时间**: {self.report.timestamp}",
            f"**检查状态**: {'✅ 通过' if self.report.passed else '❌ 未通过'}",
            f"**契约得分**: {self.report.score}/100",
            "",
            "## 摘要",
            "",
            "```",
            f"{self.report.summary}",
            "```",
            "",
            "## Schema 统计",
            "",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 后端 Schema 数 | {self.report.backend_schemas_count} |",
            f"| 前端类型数 | {self.report.frontend_schemas_count} |",
            f"| 匹配 Schema 对 | {self.report.matched_schemas} |",
            "",
        ]
        
        # 建议
        if self.report.recommendations:
            lines.extend([
                "## 建议",
                "",
            ])
            for i, rec in enumerate(self.report.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")
        
        # 问题详情
        if self.report.issues:
            lines.extend([
                "## 问题详情",
                "",
            ])
            
            # 按严重级别分组
            for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
                issues = [i for i in self.report.issues if i.severity == severity]
                if issues:
                    lines.extend([
                        f"### {self._get_severity_label_zh(severity)} ({len(issues)} 个)",
                        "",
                    ])
                    
                    for i, issue in enumerate(issues, 1):
                        lines.extend([
                            f"#### {i}. {issue.message}",
                            "",
                            f"- **规则**: `{issue.rule}`",
                            f"- **Schema**: `{issue.schema_name}`",
                        ])
                        
                        if issue.field_name:
                            lines.append(f"- **字段**: `{issue.field_name}`")
                        
                        if issue.detail:
                            lines.append(f"- **详情**: {issue.detail}")
                        
                        if issue.backend_value:
                            lines.append(f"- **后端**: `{issue.backend_value}`")
                        
                        if issue.frontend_value:
                            lines.append(f"- **前端**: `{issue.frontend_value}`")
                        
                        lines.extend([
                            "",
                            f"**修复建议**: {issue.suggestion}",
                            "",
                        ])
                        
                        if issue.backend_file:
                            lines.append(f"📄 后端位置: `{issue.backend_file}:{issue.backend_line}`")
                        
                        if issue.frontend_file:
                            lines.append(f"📄 前端位置: `{issue.frontend_file}:{issue.frontend_line}`")
                        
                        lines.append("")
        else:
            lines.extend([
                "## 检查结果",
                "",
                "✅ **未发现任何问题，前后端契约完全一致！**",
                "",
            ])
        
        return "\n".join(lines)
    
    def _to_markdown_en(self) -> str:
        """生成英文 Markdown 报告"""
        lines = [
            "# API Contract Check Report",
            "",
            f"**Check Time**: {self.report.timestamp}",
            f"**Status**: {'✅ PASSED' if self.report.passed else '❌ FAILED'}",
            f"**Contract Score**: {self.report.score}/100",
            "",
            "## Summary",
            "",
            "```",
            f"{self.report.summary}",
            "```",
            "",
            "## Schema Statistics",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Backend Schemas | {self.report.backend_schemas_count} |",
            f"| Frontend Types | {self.report.frontend_schemas_count} |",
            f"| Matched Pairs | {self.report.matched_schemas} |",
            "",
        ]
        
        # Recommendations
        if self.report.recommendations:
            lines.extend([
                "## Recommendations",
                "",
            ])
            for i, rec in enumerate(self.report.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")
        
        # Issues
        if self.report.issues:
            lines.extend([
                "## Issues",
                "",
            ])
            
            for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
                issues = [i for i in self.report.issues if i.severity == severity]
                if issues:
                    lines.extend([
                        f"### {self._get_severity_label_en(severity)} ({len(issues)})",
                        "",
                    ])
                    
                    for i, issue in enumerate(issues, 1):
                        lines.extend([
                            f"#### {i}. {issue.message}",
                            "",
                            f"- **Rule**: `{issue.rule}`",
                            f"- **Schema**: `{issue.schema_name}`",
                        ])
                        
                        if issue.field_name:
                            lines.append(f"- **Field**: `{issue.field_name}`")
                        
                        if issue.detail:
                            lines.append(f"- **Detail**: {issue.detail}")
                        
                        if issue.backend_value:
                            lines.append(f"- **Backend**: `{issue.backend_value}`")
                        
                        if issue.frontend_value:
                            lines.append(f"- **Frontend**: `{issue.frontend_value}`")
                        
                        lines.extend([
                            "",
                            f"**Suggestion**: {issue.suggestion}",
                            "",
                        ])
                        
                        if issue.backend_file:
                            lines.append(f"📄 Backend: `{issue.backend_file}:{issue.backend_line}`")
                        
                        if issue.frontend_file:
                            lines.append(f"📄 Frontend: `{issue.frontend_file}:{issue.frontend_line}`")
                        
                        lines.append("")
        else:
            lines.extend([
                "## Check Result",
                "",
                "✅ **No issues found. Backend and frontend contracts are fully consistent!**",
                "",
            ])
        
        return "\n".join(lines)
    
    def to_json(self) -> str:
        """生成 JSON 格式报告"""
        data = {
            "timestamp": self.report.timestamp,
            "passed": self.report.passed,
            "score": self.report.score,
            "summary": self.report.summary,
            "statistics": {
                "backend_schemas": self.report.backend_schemas_count,
                "frontend_schemas": self.report.frontend_schemas_count,
                "matched_schemas": self.report.matched_schemas
            },
            "recommendations": self.report.recommendations,
            "issues": [issue.to_dict() for issue in self.report.issues]
        }
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def save(self, filepath: str, format: str = "markdown", language: str = "zh"):
        """
        保存报告到文件
        
        Args:
            filepath: 文件路径
            format: 格式 (markdown, json)
            language: 语言 (zh, en)
        """
        if format == "markdown":
            content = self.to_markdown(language)
            filepath = filepath if filepath.endswith('.md') else filepath + '.md'
        elif format == "json":
            content = self.to_json()
            filepath = filepath if filepath.endswith('.json') else filepath + '.json'
        else:
            raise ValueError(f"不支持的格式: {format}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def _get_severity_label_zh(self, severity: Severity) -> str:
        """获取中文严重级别标签"""
        labels = {
            Severity.CRITICAL: "🔴 严重 (CRITICAL)",
            Severity.HIGH: "🟠 高 (HIGH)",
            Severity.MEDIUM: "🟡 中 (MEDIUM)",
            Severity.LOW: "🔵 低 (LOW)"
        }
        return labels.get(severity, severity.value)
    
    def _get_severity_label_en(self, severity: Severity) -> str:
        """获取英文严重级别标签"""
        labels = {
            Severity.CRITICAL: "🔴 CRITICAL",
            Severity.HIGH: "🟠 HIGH",
            Severity.MEDIUM: "🟡 MEDIUM",
            Severity.LOW: "🔵 LOW"
        }
        return labels.get(severity, severity.value)


# 便捷函数
def generate_markdown_report(report: ContractReport, language: str = "zh") -> str:
    """便捷函数：生成 Markdown 报告"""
    reporter = ContractReporter(report)
    return reporter.to_markdown(language)


def generate_json_report(report: ContractReport) -> str:
    """便捷函数：生成 JSON 报告"""
    reporter = ContractReporter(report)
    return reporter.to_json()


def save_report(report: ContractReport, filepath: str, format: str = "markdown", language: str = "zh"):
    """便捷函数：保存报告"""
    reporter = ContractReporter(report)
    return reporter.save(filepath, format, language)
