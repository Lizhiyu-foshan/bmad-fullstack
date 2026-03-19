# BMAD-Fullstack 闭环管理手册 (loop_instruction.md)

**版本**: v1.0  
**用途**: 全栈开发项目闭环管理流程  
**核心目标**: 确保前后端契约一致性，防止API不一致问题流入生产环境

---

## 1. 闭环管理理念

### 1.1 什么是闭环管理

```
API变更提案 → 契约审查 → 前后端同步修改 → 契约验证 → 通过/阻断
     ↑                                                      │
     └──────────────── 失败时返回修改 ←──────────────────────┘
```

**核心原则**:
- **契约优先**: API变更必须先定义契约，后实现代码
- **自动验证**: 每次提交自动检查契约一致性
- **阻断机制**: 契约不一致时自动阻断流程
- **可追溯**: 所有契约变更记录历史，便于回溯

### 1.2 闭环管理 vs 传统开发

| 维度 | 传统开发 | BMAD-Fullstack闭环管理 |
|------|----------|----------------------|
| API变更 | 口头约定，容易遗漏 | 契约文件定义，强制执行 |
| 前后端同步 | 人工检查，易出错 | 自动验证，即时反馈 |
| 发现问题 | 联调阶段才发现 | 提交前自动检查 |
| 修复成本 | 高（需改多处） | 低（早期发现） |
| 生产事故 | API不一致导致 | 基本消除 |

---

## 2. 闭环管理流程

### 2.1 标准开发流程

```
┌─────────────────────────────────────────────────────────────────┐
│                         开发流程闭环                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 需求分析                                                     │
│     ↓                                                            │
│  2. API契约设计 ←── 创建/修改契约文件 (.bmad/contracts/*.yaml)   │
│     ↓                                                            │
│  3. 契约审查 ←──── 团队成员Review契约变更                        │
│     ↓                                                            │
│  4. 前后端并行开发                                               │
│     ├── 后端: 实现Pydantic Schema                                │
│     └── 前端: 实现TypeScript Interface                           │
│     ↓                                                            │
│  5. 本地契约检查 ←── 运行 bmad-fullstack check                   │
│     ↓                                                            │
│     ├─→ ❌ 失败 → 修复不一致 → 回到步骤4                         │
│     ↓                                                            │
│     └─→ ✅ 通过                                                  │
│     ↓                                                            │
│  6. 提交代码                                                     │
│     ↓                                                            │
│  7. CI契约验证 ←── 自动运行检查                                  │
│     ↓                                                            │
│     ├─→ ❌ 失败 → PR被阻断 → 修复 → 回到步骤4                    │
│     ↓                                                            │
│     └─→ ✅ 通过 → PR可合并                                       │
│     ↓                                                            │
│  8. 联调测试                                                     │
│     ↓                                                            │
│  9. 生产部署                                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 各阶段详细说明

#### 阶段1: 需求分析
- 明确API变更需求
- 确定影响范围（哪些端点、字段变更）

#### 阶段2: API契约设计
```yaml
# .bmad/contracts/user-api.yaml
api:
  endpoint: "/api/users"
  method: "POST"
  
request:
  body:
    username: { type: "string", required: true, min: 3, max: 50 }
    email: { type: "email", required: true }
    age: { type: "integer", required: false, min: 0 }

response:
  201:
    body:
      id: { type: "uuid" }
      username: { type: "string" }
      email: { type: "email" }
      created_at: { type: "datetime" }
  
  400:
    body:
      error: { type: "string" }
      details: { type: "array", items: "string" }
```

#### 阶段3: 契约审查
审查要点：
- [ ] 字段命名符合团队规范
- [ ] 类型选择合理
- [ ] 必填/可选判断准确
- [ ] 错误处理完备
- [ ] 向后兼容（如适用）

#### 阶段4: 前后端并行开发
```python
# backend/app/schemas/user.py
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    age: Optional[int] = Field(None, ge=0)

class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    created_at: datetime
```

```typescript
// frontend/src/types/user.ts
interface UserCreate {
  username: string;  // min: 3, max: 50
  email: string;     // email format
  age?: number;      // min: 0
}

interface UserResponse {
  id: string;        // uuid
  username: string;
  email: string;
  created_at: string; // ISO8601
}
```

#### 阶段5: 本地契约检查
```bash
# 检查全部
bmad-fullstack check

# 检查特定API
bmad-fullstack check --endpoint /api/users

# 检查并生成报告
bmad-fullstack check --format html --output contract-report.html
```

#### 阶段6-7: 提交与CI验证
自动触发，无需人工干预。

---

## 3. 闭环检查点

### 3.1 预提交检查 (Pre-commit)

```bash
# .git/hooks/pre-commit
#!/bin/bash
echo "🔍 正在检查API契约一致性..."

bmad-fullstack check --ci
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "❌ 契约检查失败！"
    echo ""
    echo "请修复以下问题后再提交："
    echo "1. 检查Pydantic模型和TypeScript类型是否一致"
    echo "2. 运行 bmad-fullstack check 查看详情"
    echo "3. 如有疑问，参考 .bmad/contracts/ 下的契约定义"
    echo ""
    exit 1
fi

echo "✅ 契约检查通过！"
exit 0
```

### 3.2 CI/CD检查

**GitHub Actions阻断配置**:
```yaml
# .github/workflows/contract-check.yml
name: API Contract Check

on:
  pull_request:
    branches: [ main, develop ]

jobs:
  contract-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install BMAD-Fullstack
        run: pip install bmad-fullstack
      
      - name: Run Contract Check
        run: bmad-fullstack check --ci
      
      - name: Block if Failed
        if: failure()
        run: |
          echo "::error::API契约检查失败，无法合并PR"
          exit 1
```

### 3.3 合并前检查

**PR模板**:
```markdown
## 描述
<!-- 描述变更内容 -->

## API契约变更
<!-- 如有API变更，填写以下内容 -->
- [ ] 无API变更
- [ ] 有API变更，契约文件已更新 (.bmad/contracts/)
- [ ] 已运行本地契约检查通过

## 检查清单
- [ ] 代码遵循团队规范
- [ ] 新增/修改的API有对应TypeScript类型
- [ ] 契约检查通过 (`bmad-fullstack check`)
- [ ] 单元测试通过
- [ ] 联调测试通过（如适用）

## 契约检查报告
<!-- CI会自动生成，无需手动填写 -->
```

---

## 4. 闭环规则

### 4.1 阻断规则（必须修复）

以下情况会阻断流程：

| 规则 | 说明 | 阻断时机 |
|------|------|----------|
| FIELD_NAME_MISMATCH | 字段名不一致 | pre-commit / CI |
| TYPE_MISMATCH | 类型不匹配 | pre-commit / CI |
| MISSING_REQUIRED_FIELD | 必填字段缺失 | pre-commit / CI |
| ENUM_VALUE_MISMATCH | 枚举值不一致 | pre-commit / CI |
| BREAKING_CHANGE | 破坏性变更（未标记） | CI |

### 4.2 警告规则（建议修复）

以下情况会警告但不阻断：

| 规则 | 说明 | 处理建议 |
|------|------|----------|
| OPTIONAL_MISMATCH | 可选性不一致 | 确认是否需要同步 |
| EXTRA_FIELD | 存在额外字段 | 确认是否遗漏 |
| DEPRECATED_FIELD | 使用废弃字段 | 迁移到新字段 |
| DOC_MISSING | 缺少文档 | 补充注释说明 |

### 4.3 例外处理

如需临时忽略某些检查：

```yaml
# .bmad/project-charter.yaml
contract:
  # 临时忽略（附带原因和过期时间）
  temporary_ignores:
    - rule: "TYPE_MISMATCH"
      field: "legacy_id"
      reason: "旧系统兼容，计划v2.0移除"
      expires: "2026-06-01"
      approved_by: "tech-lead"
```

---

## 5. 问题处理流程

### 5.1 契约检查失败处理

```
检查失败
    ↓
查看报告 (bmad-fullstack check --format html)
    ↓
定位问题
    ↓
├─→ 后端Schema错误 → 修改Pydantic模型
├─→ 前端类型错误 → 修改TypeScript Interface
├─→ 契约定义错误 → 修改契约文件
└─→ 特殊情况 → 申请例外
    ↓
重新检查
    ↓
提交修复
```

### 5.2 常见问题解决方案

**问题1: "字段名不一致"**
```
❌ [FIELD_NAME_MISMATCH] UserCreate.username ≠ UserCreate.userName
```
解决方案：统一命名规范，建议后端使用snake_case，前端自动转换。

**问题2: "类型不匹配"**
```
❌ [TYPE_MISMATCH] age: int ≠ age: string
```
解决方案：确保类型映射正确，检查是否有自定义类型未配置。

**问题3: "枚举值不一致"**
```
❌ [ENUM_MISMATCH] Status: ['active', 'inactive'] ≠ ['ACTIVE', 'INACTIVE']
```
解决方案：统一枚举值大小写规范。

---

## 6. 持续改进

### 6.1 契约健康度度量

```yaml
# .bmad/metrics.yaml
metrics:
  # 每周统计
  weekly:
    - contract_violations      # 契约违规次数
    - fix_time_average         # 平均修复时间
    - false_positive_rate      # 误报率
    - coverage_percentage      # API覆盖率
  
  # 目标值
  targets:
    contract_violations: 0
    fix_time_average: "< 30min"
    false_positive_rate: "< 5%"
    coverage_percentage: "> 90%"
```

### 6.2 团队反馈机制

每月召开契约质量回顾会：
1. 审查本月契约违规情况
2. 分析高频问题根因
3. 优化检查规则
4. 更新团队规范

### 6.3 规则演进

```
规则提案 → 团队讨论 → 试点运行 → 效果评估 → 正式启用
    ↑                                              ↓
    └────────────── 效果不佳时回滚 ────────────────┘
```

---

## 7. 团队协作规范

### 7.1 角色职责

| 角色 | 职责 |
|------|------|
| **后端开发** | 维护Pydantic Schema，确保与契约一致 |
| **前端开发** | 维护TypeScript类型，确保与契约一致 |
| **技术负责人** | 审查契约变更，批准例外申请 |
| **架构师** | 制定API规范，优化检查规则 |

### 7.2 沟通规范

**契约变更通知模板**:
```markdown
## API契约变更通知

**影响端点**: /api/users
**变更类型**: 新增字段
**变更内容**:
- 新增 `phone` 字段 (string, optional)
- 原因: 支持手机号登录

**涉及人员**: @backend-dev @frontend-dev
**截止日期**: 2026-03-25

**相关PR**: #123
```

### 7.3 代码审查关注点

审查者需确认：
- [ ] 契约文件是否同步更新
- [ ] 前后端类型是否一致
- [ ] 是否引入了破坏性变更
- [ ] 错误处理是否完备

---

## 8. 工具与命令速查

### 8.1 日常命令

```bash
# 检查契约
bmad-fullstack check

# 检查并修复
bmad-fullstack check --fix

# 检查特定API
bmad-fullstack check --endpoint /api/users

# 生成报告
bmad-fullstack check --format html --output report.html

# 查看历史
bmad-fullstack history

# 诊断问题
bmad-fullstack doctor
```

### 8.2 CI专用命令

```bash
# 非交互模式
bmad-fullstack check --ci

# JSON格式输出
bmad-fullstack check --ci --format json

# 严格模式（任何警告都失败）
bmad-fullstack check --ci --strict
```

---

## 9. 成功指标

### 9.1 量化指标

| 指标 | 目标值 | 测量方式 |
|------|--------|----------|
| API不一致导致的Bug | 0 | Bug追踪系统 |
| 契约检查通过率 | > 95% | CI统计 |
| 平均修复时间 | < 30分钟 | 日志分析 |
| API覆盖率 | > 90% | 检查工具 |

### 9.2 定性指标

- 前后端沟通效率提升
- 联调时间缩短
- 生产环境API问题减少
- 团队对API规范达成共识

---

## 10. 附录

### 10.1 相关文档

- [setting.md](./setting.md) - 配置手册
- [SKILL.md](./SKILL.md) - 框架功能说明
- BMAD-EVO文档（AST审计引擎）

### 10.2 版本历史

- v1.0 (2026-03-19): 初始版本，建立闭环管理流程

### 10.3 反馈渠道

- 问题反馈: GitHub Issues
- 功能建议: GitHub Discussions
- 紧急联系: tech-lead@example.com

---

**核心理念**: 
> "契约即法律，检查即保险，闭环即质量。"

**记住**: 预防胜于治疗，早期发现API不一致问题，避免后期高昂修复成本。
