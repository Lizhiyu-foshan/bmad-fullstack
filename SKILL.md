---
name: bmad-fullstack
description: BMAD-Fullstack 全栈开发约束检查框架。专门面向复杂前后端系统开发，提供 API 契约检查、前后端类型同步、跨语言类型映射验证。与 BMAD-EVO 共享 AST 审计引擎，独立版本迭代。
---

# BMAD-Fullstack v1.0

**全栈开发类型安全卫士** - API 契约检查 + 前后端同步 + 跨语言验证

## 定位

与 BMAD-EVO 的区别：

| 维度 | BMAD-EVO | BMAD-Fullstack |
|-----|----------|----------------|
| **目标用户** | Python 开发者、Skill 作者 | 全栈工程师、前后端团队 |
| **核心场景** | 后端代码质量、Skill 开发 | 前后端契约一致性 |
| **检查范围** | Python 单语言 | Python + TypeScript 跨语言 |
| **创新功能** | AST 约束审计 | API 契约自动验证 |
| **项目规模** | 中小型 | 中大型全栈系统 |

## 核心价值

1. **API 契约自动验证** - 避免 80% 前后端联调问题
2. **类型安全端到端** - Pydantic ↔ TypeScript 类型同步
3. **框架无关** - FastAPI/Flask/Django + React/Vue/Next.js
4. **流程阻断** - 契约不一致时自动阻断，防止问题流入生产

## 架构

```
BMAD-Fullstack
│
├── lib/
│   ├── api_contract/          # API 契约检查核心
│   │   ├── types.py           # 统一数据类型定义
│   │   ├── checker.py         # 契约检查器
│   │   ├── normalizer.py      # Schema 标准化
│   │   └── type_mapper.py     # 跨语言类型映射
│   │
│   ├── parsers/
│   │   ├── pydantic_parser.py # Python/Pydantic 解析
│   │   └── typescript_parser.py # TypeScript AST 解析
│   │
│   ├── reporters/
│   │   └── contract_reporter.py # 报告生成
│   │
│   ├── validators/
│   │   └── field_validators.py  # 字段验证规则
│   │
│   └── ast_auditor.py -> (symlink to bmad-evo)  # AST 引擎共享
│
├── agents/
│   ├── contract_auditor.py    # 契约审计 Agent
│   └── phase_gateway_adapter.py # Phase Gateway 适配
│
├── templates/
│   ├── constraints/
│   │   ├── api-contract.yaml       # 基础 API 契约约束
│   │   ├── fastapi-react.yaml      # FastAPI + React 模板
│   │   ├── django-vue.yaml         # Django + Vue 模板
│   │   └── nest-nextjs.yaml        # NestJS + Next.js 模板
│   │
│   └── projects/
│       ├── fullstack-basic/        # 基础全栈项目模板
│       └── fullstack-advanced/     # 高级全栈项目模板
│
├── scripts/
│   ├── validate_contract.py   # CLI 验证工具
│   └── generate_types.py      # 类型生成工具（Phase 2.5）
│
├── tests/
│   ├── test_pydantic_parser.py
│   ├── test_typescript_parser.py
│   └── test_contract_checker.py
│
└── bmad-fullstack              # CLI 入口
```

## 快速开始

### 1. 初始化全栈项目

```bash
# 创建 FastAPI + React 项目
bmad-fullstack init --template fastapi-react --name my-fullstack-app

# 创建 Django + Vue 项目
bmad-fullstack init --template django-vue --name my-fullstack-app
```

### 2. 配置 API 契约

```yaml
# .bmad/project-charter.yaml
project:
  name: "用户管理系统"
  type: "fullstack"

backend:
  framework: "fastapi"
  schema_path: "backend/app/schemas"
  main_file: "backend/app/main.py"

frontend:
  framework: "react"
  type_path: "frontend/src/types"
  api_client_path: "frontend/src/api"

contract:
  check_field_names: true
  check_field_types: true
  check_required: true
  check_enums: true
  type_strictness: "strict"  # strict | loose
```

### 3. 运行契约检查

```bash
# 检查整个项目
bmad-fullstack check

# 检查特定 API
bmad-fullstack check --endpoint /api/users

# CI/CD 模式（非交互）
bmad-fullstack check --ci
```

### 4. 查看报告

```bash
# 生成 HTML 报告
bmad-fullstack check --format html --output contract-report.html

# 查看历史
bmad-fullstack history
```

## 核心功能

### API 契约检查

验证前后端 Schema 一致性：

```python
# backend/schemas/user.py
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    age: Optional[int] = None
```

```typescript
// frontend/src/types/user.ts
interface UserCreate {
  username: string;
  email: string;
  age?: number;
}
```

**检查项**：
- ✅ 字段名称一致（`username` ↔ `username`）
- ✅ 类型匹配（`str` ↔ `string`）
- ✅ 必填/可选一致（`Optional` ↔ `?`）
- ✅ 枚举值一致
- ✅ 嵌套结构一致

### 类型映射

自动处理 Python ↔ TypeScript 类型转换：

| Python | TypeScript | 备注 |
|--------|-----------|------|
| `str` | `string` | |
| `int` | `number` | |
| `float` | `number` | |
| `bool` | `boolean` | |
| `List[T]` | `T[]` | 数组 |
| `Dict[K,V]` | `Record<K,V>` | 字典 |
| `Optional[T]` | `T \| undefined` | 可选 |
| `datetime` | `string` | ISO8601 |
| `UUID` | `string` | |
| `EmailStr` | `string` | 带格式验证 |

### 与 BMAD-EVO 集成

复用 Phase Gateway 进行流程控制：

```python
# 在 BMAD-EVO 工作流中调用
from bmad_fullstack.api_contract import ContractChecker

checker = ContractChecker(project_path)
result = checker.validate()

if not result.passed:
    # 阻断流程
    gateway.block_phase("contract_validation_failed")
```

## CLI 命令

```bash
# 项目命令
bmad-fullstack init [--template] [--name]     # 初始化项目
bmad-fullstack check [--endpoint] [--format]   # 检查契约
bmad-fullstack fix [--auto]                    # 自动修复不一致
bmad-fullstack history                         # 查看检查历史
bmad-fullstack generate-types [--target]       # 生成类型（Phase 2.5）

# 配置命令
bmad-fullstack config set <key> <value>        # 设置配置
bmad-fullstack config get <key>                # 获取配置
bmad-fullstack config list                     # 列出配置

# 诊断命令
bmad-fullstack doctor                          # 诊断环境
bmad-fullstack version                         # 查看版本
```

## 版本规划

### v1.0（当前）- API 契约检查核心
- [x] Python Pydantic Schema 提取
- [ ] TypeScript Interface 解析（进行中）
- [ ] 基础类型映射
- [ ] 字段一致性检查
- [ ] Markdown/JSON 报告

### v1.1 - 高级类型支持
- [ ] 泛型参数解析（`List[User]`, `Response<T>`）
- [ ] 联合类型处理（`Union[str, int]` ↔ `string | number`）
- [ ] 嵌套 Schema 深度检查
- [ ] 枚举类型同步

### v1.2 - 框架集成
- [ ] FastAPI 路由自动发现
- [ ] OpenAPI 规范对比
- [ ] React/Vue PropTypes 检查
- [ ] 框架特定规则

### v2.0（Phase 2.5）- 自动生成
- [ ] Pydantic → TypeScript 类型生成
- [ ] TypeScript → Pydantic 类型生成
- [ ] 增量更新（只变更修改的部分）
- [ ] CI/CD 集成

## 与 BMAD-EVO 的关系

```
BMAD-EVO (Backend/Skill Focus)
    │
    ├── 共享: AST Auditing Engine
    │
    └── 独立: Phase Gateway, Constraint Checker

BMAD-Fullstack (Fullstack Focus)
    │
    ├── 共享: AST Auditing Engine (symlink)
    │
    └── 独立: API Contract Checker, TypeScript Parser
```

**共享组件**：
- `lib/ast_auditor.py` - Python AST 审计引擎（软链接）
- Phase Gateway 接口规范（复用，不依赖）

**独立组件**：
- 版本号、发布周期、Issue 跟踪
- TypeScript AST 解析器（npm 依赖）
- API 契约检查核心逻辑

## 贡献指南

### 开发环境

```bash
# 克隆仓库
git clone https://github.com/openclaw/bmad-fullstack.git
cd bmad-fullstack

# 安装依赖
pip install -r requirements.txt
npm install typescript  # 用于 TS AST 解析

# 运行测试
pytest tests/
```

### 提交规范

- `feat:` 新功能
- `fix:` 修复
- `docs:` 文档
- `test:` 测试
- `refactor:` 重构

## 许可证

MIT License - 与 BMAD-EVO 保持一致

---

**Created**: 2026-03-18
**Version**: 1.0.0-alpha
**Maintainer**: Kimi Claw
**Status**: 开发中
