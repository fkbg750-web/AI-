# Contributing to TeamMind

感谢您对 TeamMind 的兴趣！欢迎贡献代码。

## 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/yourusername/teammind.git
cd teammind

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -e ".[dev]"

# 启动数据库
docker-compose up -d
```

## 开发流程

1. **Fork** 本仓库
2. 创建特性分支: `git checkout -b feature/amazing-feature`
3. 提交更改: `git commit -m 'Add amazing feature'`
4. Push 分支: `git push origin feature/amazing-feature`
5. 创建 **Pull Request**

## 代码规范

- 使用 `ruff` 进行代码检查: `ruff check src/`
- 使用 `mypy` 进行类型检查: `mypy src/`
- 运行测试: `pytest`

## 提交信息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

类型 (type):
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

## 测试

```bash
# 运行所有测试
pytest

# 带覆盖率
pytest --cov=src tests/

# 只运行特定文件
pytest tests/test_agents.py
```

## 问题反馈

请通过 [GitHub Issues](https://github.com/yourusername/teammind/issues) 反馈问题。

---

再次感谢您的贡献！
