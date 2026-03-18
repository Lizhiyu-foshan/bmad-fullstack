"""
Contract Reporter - 契约检查报告生成器
生成 Markdown/JSON/HTML 报告
"""

import json
from typing import List, Optional
from datetime import datetime

from ..api_contract.types import ContractReport, ContractIssue, Severity


class ContractReporter:
    """契约检查报告生成器"""
    
    def __init__(self, report: ContractReport):
        self.report = report
    
    def to_markdown(self) -> str:
        """生成 Markdown 格式报告"""
        lines = [
            "# API 契约检查报告",
            "",
            f"**检查时间**: {self.report.timestamp}",
            f"**检查状态**: {'✅ 通过' if self.report.passed else '❌ 未通过'}",
            f"**契约得分**: {self.report.score}/100",
            "",
            "## 摘要",
            "",
            f"```",
            f"{self.report.summary}",
            f"```",
            "",
            "## Schema 统计",
            "",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 总 Schema 数 | {self.report.total_schemas} |",
            f"| 匹配 Schema 对 | {self.report.matched_schemas} |",
            f"| 不匹配数量 | {self.report.mismatched_schemas} |",
            "",
        ]
        
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
                        f"### {self._get_severity_label(severity)} ({len(issues)} 个)",
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
                        
                        lines.extend([
                            "",
                            f"**建议**: {issue.suggestion}",
                            "",
                        ])
        else:
            lines.extend([
                "## 检查结果",
                "",
                "✅ **未发现任何问题，前后端契约完全一致！**",
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
                "total_schemas": self.report.total_schemas,
                "matched_schemas": self.report.matched_schemas,
                "mismatched_schemas": self.report.mismatched_schemas
            },
            "issues": [
                {
                    "severity": issue.severity.value,
                    "rule": issue.rule,
                    "message": issue.message,
                    "schema_name": issue.schema_name,
                    "field_name": issue.field_name,
                    "suggestion": issue.suggestion
                }
                for issue in self.report.issues
            ]
        }
        
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def to_html(self) -> str:
        """生成 HTML 格式报告"""
        severity_colors = {
            Severity.CRITICAL: "#dc3545",
            Severity.HIGH: "#fd7e14",
            Severity.MEDIUM: "#ffc107",
            Severity.LOW: "#6c757d"
        }
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API 契约检查报告</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }}
        .header {{
            background: {'#28a745' if self.report.passed else '#dc3545'};
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .score {{
            font-size: 48px;
            font-weight: bold;
        }}
        .summary {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .issue {{
            border-left: 4px solid #ccc;
            padding: 15px;
            margin-bottom: 15px;
            background: #fff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .issue-critical {{ border-left-color: {severity_colors[Severity.CRITICAL]}; }}
        .issue-high {{ border-left-color: {severity_colors[Severity.HIGH]}; }}
        .issue-medium {{ border-left-color: {severity_colors[Severity.MEDIUM]}; }}
        .issue-low {{ border-left-color: {severity_colors[Severity.LOW]}; }}
        .severity {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            color: white;
            font-size: 12px;
            font-weight: bold;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #dee2e6;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background: #e9ecef;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>API 契约检查报告</h1>
        <div class="score">{self.report.score}/100</div>
        <p>{'✅ 通过' if self.report.passed else '❌ 未通过'} | 检查时间: {self.report.timestamp}</p>
    </div>
    
    <div class="summary">
        <h2>摘要</h2>
        <pre>{self.report.summary}</pre>
    </div>
    
    <h2>Schema 统计</h2>
    <table>
        <tr><th>指标</th><th>数值</th></tr>
        <tr><td>总 Schema 数</td><td>{self.report.total_schemas}</td></tr>
        <tr><td>匹配 Schema 对</td><td>{self.report.matched_schemas}</td></tr>
        <tr><td>不匹配数量</td><td>{self.report.mismatched_schemas}</td></tr>
    </table>
    
    <h2>问题详情 ({len(self.report.issues)} 个)</h2>
"""
        
        for issue in self.report.issues:
            severity_class = f"issue-{issue.severity.value.lower()}"
            severity_color = severity_colors.get(issue.severity, "#6c757d")
            
            html += f"""
    <div class="issue {severity_class}">
        <span class="severity" style="background: {severity_color}">{issue.severity.value}</span>
        <h3>{issue.message}</h3>
        <p><strong>规则:</strong> <code>{issue.rule}</code></p>
        <p><strong>Schema:</strong> <code>{issue.schema_name}</code></p>
        {f'<p><strong>字段:</strong> <code>{issue.field_name}</code></p>' if issue.field_name else ''}
        <p><strong>建议:</strong> {issue.suggestion}</p>
    </div>
"""
        
        html += """
</body>
</html>
"""
        
        return html
    
    def save(self, filepath: str, format: str = "markdown"):
        """保存报告到文件"""
        if format == "markdown":
            content = self.to_markdown()
            filepath = filepath if filepath.endswith('.md') else filepath + '.md'
        elif format == "json":
            content = self.to_json()
            filepath = filepath if filepath.endswith('.json') else filepath + '.json'
        elif format == "html":
            content = self.to_html()
            filepath = filepath if filepath.endswith('.html') else filepath + '.html'
        else:
            raise ValueError(f"不支持的格式: {format}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def _get_severity_label(self, severity: Severity) -> str:
        """获取严重级别标签"""
        labels = {
            Severity.CRITICAL: "🔴 严重 (CRITICAL)",
            Severity.HIGH: "🟠 高 (HIGH)",
            Severity.MEDIUM: "🟡 中 (MEDIUM)",
            Severity.LOW: "🔵 低 (LOW)"
        }
        return labels.get(severity, severity.value)
