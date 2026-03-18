# BMAD-Fullstack

**全栈开发约束检查框架** - API 契约检查 + 前后端类型同步 + 跨语言验证

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange)](https://github.com/openclaw/bmad-fullstack)

## 与 BMAD-EVO 的关系

BMAD-Fullstack 是 BMAD-EVO 的姊妹项目，专注于**全栈开发的 API 契约检查**。

| 特性 | BMAD-EVO | BMAD-Fullstack |
|------|----------|----------------|
| 目标用户 | Python 开发者、Skill 作者 | 全栈工程师、前后端团队 |
| 核心场景 | 后端代码质量、Skill 开发 | 前后端契约一致性 |
| 检查范围 | Python 单语言 | Python + TypeScript 跨语言 |
| 创新功能 | AST 约束审计 | API 契约自动验证 |

**技术共享**：
- ✅ 共享 `ast_auditor.py` AST 审计引擎
- ✅ 复用 Phase Gateway 流程控制
- ✅ 独立版本迭代

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/openclaw/bmad-fullstack.git
cd bmad-fullstack

# 安装依赖
pip install -r requirements.txt

# 可选：安装 TypeScript 解析器（npm）
npm install -g typescript
```

### 初始化项目

```bash
# 创建 FastAPI + React 项目
./bmad-fullstack init --template fastapi-react --name my-fullstack-app

cd my-fullstack-app
```

### 配置项目

编辑 `.bmad/project-charter.yaml`：

```yaml
project:
  name: "my-fullstack-app"
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
  type_strictness: "strict"
```

### 运行检查

```bash
# 检查契约一致性
./bmad-fullstack check

# 生成 HTML 报告
./bmad-fullstack check --format html --output report.html

# CI 模式
./bmad-fullstack check --ci
```

## 核心功能

### API 契约检查

自动对比前后端 Schema：

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
- ✅ 字段名称一致
- ✅ 类型匹配（`str` ↔ `string`）
- ✅ 必填/可选一致（`Optional` ↔ `?`）
- ✅ 枚举值一致
- ✅ 嵌套结构一致

### 类型映射

| Python | TypeScript |
|--------|-----------|
| `str` | `string` |
| `int` | `number` |
| `float` | `number` |
| `bool` | `boolean` |
| `List[T]` | `T[]` |
| `Dict[K,V]` | `Record<K,V>` |
| `Optional[T]` | `T \| undefined` |
| `datetime` | `string` (ISO8601) |
| `UUID` | `string` |

## CLI 命令

```bash
# 项目命令
bmad-fullstack init [--template] [--name]     # 初始化项目
bmad-fullstack check [--format] [--output]     # 检查契约
bmad-fullstack version                         # 查看版本
```

## 架构

```
bmad-fullstack/
├── lib/
│   ├── api_contract/          # 契约检查核心
│   │   ├── types.py           # 数据类型定义
│   │   ├── checker.py         # 契约检查器
│   │   ├── normalizer.py      # Schema 标准化
│   │   └── type_mapper.py     # 类型映射
│   │
│   ├── parsers/
│   │   ├── pydantic_parser.py # Python/Pydantic 解析
│   │   └── typescript_parser.py # TypeScript 解析
│   │
│   ├── reporters/             # 报告生成
│   │
│   └── ast_auditor.py ->      # 软链接到 BMAD-EVO
│
├── bmad-fullstack              # CLI 入口
└── SKILL.md                    # Skill 定义
```

## 版本规划

### v1.0（当前）- API 契约检查核心
- ✅ Python Pydantic Schema 提取
- 🚧 TypeScript Interface 解析
- ✅ 基础类型映射
- ✅ 字段一致性检查
- ✅ Markdown/JSON/HTML 报告

### v1.1 - 高级类型支持
- 泛型参数解析
- 联合类型处理
- 嵌套 Schema 深度检查

### v1.2 - 框架集成
- FastAPI 路由自动发现
- OpenAPI 规范对比
- React/Vue 组件检查

### v2.0 - 自动生成（Phase 2.5）
- Pydantic → TypeScript 类型生成
- 增量更新
- CI/CD 集成

## 开发

```bash
# 运行测试
pytest tests/

# 代码检查
python -m py_compile lib/**/*.py

# 类型检查
mypy lib/
```

## 贡献

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

MIT License - 与 BMAD-EVO 保持一致

---

**BMAD-Fullstack** - 让前后端契约不再断裂
