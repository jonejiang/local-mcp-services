# 🏜️ Local MCP Services Sandbox

这是一个用于安全测试的沙箱环境，与主工作区隔离。

## 用途

- 测试 `local-mcp-build.sh` 部署脚本
- 运行测试套件
- 尝试新功能而不影响主环境

## 与主环境的区别

| 项目 | 主环境 | 沙箱环境 |
|------|--------|----------|
| 路径 | `.../local-mcp-services` | `.../local-mcp-sandbox` |
| Git 分支 | `main` | `sandbox` |
| Docker 容器 | 生产环境 | 测试环境 (不同端口) |

## 快速开始

```bash
cd /Users/jone/AI/Agents/local-mcp-sandbox

# 运行测试（不启动后端服务）
python3 test_comprehensive.py

# 或使用 pytest
pytest tests/ -v --tb=short -k "not backend"

# 一键部署（会启动 Docker 容器）
bash local-mcp-build.sh
```

## 安全测试

### 可在沙箱中安全测试的内容

1. **注入攻击测试**
   ```bash
   pytest tests/test_injection.py -v
   ```

2. **速率限制测试**
   ```bash
   pytest tests/test_rate_limit.py -v
   ```

3. **并发测试**
   ```bash
   pytest tests/test_concurrency.py -v
   ```

4. **畸形输入测试**
   ```bash
   pytest tests/test_malformed.py -v
   ```

5. **审计日志测试**
   ```bash
   pytest tests/test_audit_logging.py -v
   ```

### 建议不测试的内容

- CVE 检查（需要实际 Docker 环境）
- 平台安全测试（可能影响主机）

## Docker 容器命名

沙箱环境使用不同的容器名称避免冲突：

| 服务 | 主环境 | 沙箱环境 |
|------|--------|----------|
| SearXNG | searxng | searxng-sandbox |
| EasyOCR | easyocr | easyocr-sandbox |
| Playwright | playwright | playwright-sandbox |
| Firecrawl | firecrawl | firecrawl-sandbox |

## 清理沙箱

```bash
# 停止沙箱中的容器
docker compose down

# 删除沙箱工作区
cd /Users/jone/AI/Agents
git worktree remove local-mcp-sandbox
git branch -d sandbox
```

## 注意事项

⚠️ 沙箱环境虽然隔离了代码和容器，但：
- Docker 守护进程是共享的
- 端口可能冲突（已在 docker-compose 中避免）
- 磁盘空间共享
