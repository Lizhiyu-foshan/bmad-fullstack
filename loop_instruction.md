# BMAD-Fullstack 闭环管理手册 (loop_instruction.md)

**版本**: v1.1  
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

# 附录A：开发者快速参考

## A.1 完整迭代流程示例

### 阶段0: 需求输入与评估

```yaml
# .bmad/features/feature-XXX.yaml
feature:
  id: "FEAT-001"
  name: "用户认证系统"
  status: "ready"
  
  description: |
    实现用户注册、登录、JWT Token 认证
  
  api_changes:
    new_schemas:
      - name: "UserRegister"
        fields:
          username: string (required, 3-50字符)
          email: string (required, email格式)
          password: string (required, 6-20字符)
      
      - name: "AuthResponse"
        fields:
          access_token: string (required)
          token_type: string (default: "bearer")
          expires_in: integer (required)
  
  impact:
    backend:
      - 新增 auth 模块
      - 新增 JWT 依赖
    frontend:
      - 新增登录页面
      - 新增注册页面
```

### 第1步：后端开发 + 审计 + 测试

```python
# backend/app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field, ValidationError
from fastapi import HTTPException

class UserRegister(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=20)
    
    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValueError('用户名只能包含字母和数字')
        return v

# 路由中添加异常处理
@router.post("/auth/register")
async def register(user: UserRegister):
    try:
        return AuthResponse(access_token="xxx", expires_in=3600)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"注册失败: {e}")
        raise HTTPException(status_code=500, detail="内部服务器错误")
```

**审计**：
```bash
bmad-evo audit --file backend/app/schemas/auth.py
```

**测试**：
```python
# backend/tests/test_auth.py
import pytest
from app.schemas.auth import UserRegister

def test_user_register_schema():
    """测试用户注册 Schema"""
    data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "123456"
    }
    user = UserRegister(**data)
    assert user.username == "testuser"
    
    # 边界情况
    with pytest.raises(ValueError):
        UserRegister(username="ab", email="test@example.com", password="123456")
```

### 第2步：生成前端类型 + 前端开发

```bash
bmad-fullstack generate-ts \
  --input backend/app/schemas \
  --output frontend/src/types/api.ts
```

```tsx
// frontend/src/pages/Register.tsx
import { useState } from 'react';
import { UserRegister } from '../types/api';
import { authApi } from '../api/auth';

export function RegisterPage() {
  const [form, setForm] = useState<UserRegister>({
    username: '',
    email: '',
    password: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const response = await authApi.register(form);
    localStorage.setItem('token', response.accessToken);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        value={form.username}
        onChange={e => setForm({...form, username: e.target.value})}
        placeholder="用户名"
      />
      <button type="submit">注册</button>
    </form>
  );
}
```

### 第3步：契约一致性检查

```bash
bmad-fullstack check --strict
```

### 第4步：集成测试 + 联调

```python
# backend/tests/test_integration_auth.py
def test_register_and_login():
    """测试注册和登录流程"""
    # 1. 注册
    register_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "123456"
    }
    response = client.post("/api/auth/register", json=register_data)
    assert response.status_code == 200
    
    # 2. 登录
    login_data = {
        "email": "test@example.com",
        "password": "123456"
    }
    response = client.post("/api/auth/login", json=login_data)
    assert response.status_code == 200
```

## A.2 Bug修复闭环流程

```
发现 Bug
    ↓
┌────────────────────────────────────────────────────────┐
│  分类 Bug 类型                                          │
│  1. 契约不一致 → 修改 Schema + 重新生成                  │
│  2. 后端逻辑错误 → 修改后端 + 重新审计 + 测试             │
│  3. 前端逻辑错误 → 修改前端 + 重新审计                   │
│  4. 需求理解错误 → 更新契约 + 重新开发                   │
└────────────────────────────────────────────────────────┘
    ↓
执行修复
    ↓
重新执行完整的迭代循环
    ↓
✅ 关闭 Bug
```

### Bug修复示例

```bash
# Bug 报告: 注册时用户名可以包含特殊字符

# 1. 分析: 后端验证不完善（类型2 Bug）

# 2. 修改后端 Schema
# backend/app/schemas/auth.py
class UserRegister(BaseModel):
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50,
        pattern=r'^[a-zA-Z0-9_]+$'
    )

# 3. 重新审计
bmad-evo audit --file backend/app/schemas/auth.py

# 4. 重新测试
pytest backend/tests/test_auth.py -v

# 5. 重新生成前端类型
bmad-fullstack generate-ts --input backend/app/schemas --output frontend/src/types/api.ts

# 6. 重新检查契约
bmad-fullstack check --strict

# 7. 集成测试
pytest backend/tests/test_integration_auth.py -v

# 8. 联调验证
```

## A.3 日常开发命令速查表

```bash
# ========== 日常开发迭代 ==========

# 1. 拉取最新代码
git pull origin main

# 2. 查看待办需求
cat .bmad/features/feature-XXX.yaml

# 3. 开始开发前：检查当前契约状态
bmad-fullstack check --backend backend/app/schemas

# 4. 后端开发...
vim backend/app/schemas/xxx.py

# 5. 后端开发完成：审计 + 测试
bmad-evo audit --file backend/app/schemas/xxx.py
pytest backend/tests/test_xxx.py -v

# 6. 生成前端类型
bmad-fullstack generate-ts \
  --input backend/app/schemas \
  --output frontend/src/types/api.ts

# 7. 前端开发...
vim frontend/src/pages/Xxx.tsx

# 8. 前端开发完成：审计
cd frontend && npx tsc --noEmit && npm run lint

# 9. 最终契约检查
bmad-fullstack check --strict

# 10. 集成测试
pytest backend/tests/test_integration_xxx.py -v

# 11. 提交代码
git add .
git commit -m "feat: 实现 XXX 功能

- 新增 Xxx Schema
- 实现 API 端点
- 前端页面开发
- 通过 BMAD-EVO 审计
- 通过 BMAD-Fullstack 契约检查"

# 12. CI 自动执行审计和测试
git push origin feature/xxx
```

## A.4 关键原则速记

| 原则 | 说明 |
|------|------|
| **契约优先** | 任何需求变更先更新契约文档，再开发 |
| **审计驱动** | 后端代码必须通过 BMAD-EVO 审计（85分） |
| **类型生成** | 前端类型必须从后端自动生成，禁止手撕 |
| **一致性检查** | 每次提交前必须检查前后端契约一致性 |
| **测试覆盖** | 每个 Schema 必须有单元测试，每个 API 必须有集成测试 |
| **Bug闭环** | 发现 Bug → 分类 → 修复 → 重新走完整流程 |

---

# 附录B：相关文档

- [setting.md](./setting.md) - 配置手册
- [SKILL.md](./SKILL.md) - 框架功能说明
- BMAD-EVO文档（AST审计引擎）

---

**版本历史**:
- v1.1 (2026-03-19): 整合开发者实操附录，添加完整代码示例和命令速查表
- v1.0 (2026-03-19): 初始版本，建立闭环管理流程

**核心理念**: 
> "契约即法律，检查即保险，闭环即质量。"

**记住**: 预防胜于治疗，早期发现API不一致问题，避免后期高昂修复成本。
