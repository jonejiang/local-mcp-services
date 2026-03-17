# Local MCP Services

本地 MCP 服务部署 - Docker 容器化

## 服务列表

| 服务 | 端口 | 功能 |
|------|------|------|
| SearXNG | 18880 | Web 搜索 |
| EasyOCR | 18881 | OCR 文字识别 |
| Playwright | 18882 | 网页抓取/自动化 |
| Firecrawl | 18883 | 文档解析/PDF读取 |

## 快速开始

### 构建镜像

```bash
cd local-mcp-services
docker-compose build
```

### 启动服务

```bash
docker-compose up -d
```

### 验证服务

```bash
# 运行验证脚本
./validate.sh

# 或手动检查
curl http://localhost:18880/health
curl http://localhost:18881/health
curl http://localhost:18882/health
curl http://localhost:18883/health
```

## Claude Code 配置

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "local-search": {
      "url": "http://localhost:18880/mcp"
    },
    "local-ocr": {
      "url": "http://localhost:18881/mcp"
    },
    "local-playwright": {
      "url": "http://localhost:18882/mcp"
    },
    "local-firecrawl": {
      "url": "http://localhost:18883/mcp"
    }
  }
}
```

## 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行冒烟测试
pytest tests/test_smoke.py -v

# 运行安全测试
pytest tests/test_security.py -v
```

## API 使用

### SearXNG 搜索

```bash
curl -X POST http://localhost:18880/search \
  -H "Content-Type: application/json" \
  -d '{"q": "python programming"}'
```

### EasyOCR

```bash
# 使用 URL
curl -X POST http://localhost:18881/ocr \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/image.png"}'

# 使用 Base64
curl -X POST http://localhost:18881/ocr \
  -H "Content-Type: application/json" \
  -d '{"image": "<base64_data>"}'
```

### Playwright

```bash
curl -X POST http://localhost:18882/navigate \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Firecrawl

```bash
curl -X POST http://localhost:18883/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## 安全特性

- 非 root 用户运行 (UID 1000)
- 只读文件系统
- 内存和 CPU 限制
- 能力集最小化 (cap_drop: ALL)
- SSRF 防护
- 网络隔离 (mcp-net)

## 停止服务

```bash
docker-compose down
```

## 清理

```bash
docker-compose down -v  # 删除数据卷
```
