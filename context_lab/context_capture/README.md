# Context Lab 上下文捕获模块

上下文捕获模块是 Context Lab 系统的核心组件之一，负责从多种来源收集上下文信息。本模块提供了多种捕获器，用于从不同渠道获取上下文数据。

## 模块概述

上下文捕获模块包含以下捕获器：

1. **截图捕获器 (ScreenshotCapture)**：定期捕获屏幕截图
2. **文件夹监控器 (FileMonitorCapture)**：监控文件夹变化并捕获文件内容
3. **数据流轮询器 (DataStreamPollingCapture)**：定期轮询数据源并捕获数据
4. **聊天历史捕获器 (ChatHistoryCapture)**：通过MCP接口获取聊天历史
5. **AI对话捕获器 (AIConversationCapture)**：通过MCP接口获取AI对话

所有捕获器都继承自 `BaseContextCapture` 基类，遵循统一的接口规范。

## 捕获器详情

### 1. 截图捕获器 (ScreenshotCapture)

定期捕获屏幕截图，支持图像去重和分辨率调整。

**主要特性：**
- 可配置的截图间隔
- 图像去重，避免存储相同的截图
- 支持调整截图分辨率
- 自动清理旧截图，控制存储空间

**配置示例：**
```python
config = {
    "interval": 2.0,           # 截图间隔（秒）
    "save_path": "./screenshots",  # 截图保存路径
    "max_storage": 1000,       # 最大保存数量
    "deduplication": True,     # 启用图像去重
    "resolution": "1280x720",  # 调整分辨率（可选）
}
```

### 2. 文件夹监控器 (FileMonitorCapture)

监控指定文件夹的变化，检测文件创建、修改和删除事件，并读取文件内容。

**主要特性：**
- 支持监控多个文件夹
- 文件模式过滤（包含和排除）
- 可选的递归监控子文件夹
- 自动检测文件类型和编码

**配置示例：**
```python
config = {
    "paths": ["/path/to/folder1", "/path/to/folder2"],  # 监控路径
    "patterns": ["*.txt", "*.md", "*.pdf"],             # 包含的文件模式
    "ignore_patterns": [".git/*", "*.tmp"],             # 排除的文件模式
    "recursive": True,                                  # 递归监控子文件夹
    "watch_events": ["created", "modified", "deleted"], # 监控的事件类型
    "max_file_size": 10485760,                          # 最大文件大小（字节）
}
```

### 3. 数据流轮询器 (DataStreamPollingCapture)

定期轮询数据源（如REST API、RSS Feed、GraphQL），支持增量获取数据。

**主要特性：**
- 支持多种数据源类型（REST、RSS、GraphQL）
- 增量获取数据，避免重复处理
- 可配置的轮询间隔和数据量限制
- 支持认证和错误恢复

**配置示例：**
```python
config = {
    "polling_interval": 60.0,  # 轮询间隔（秒）
    "max_items_per_poll": 100, # 每次轮询最大获取条目数
    "initial_lookback": 3600,  # 初始回溯时间（秒）
    "sources": [
        {
            "id": "news_feed",
            "name": "新闻源",
            "type": "rss",
            "url": "https://example.com/feed.xml",
            "headers": {"User-Agent": "Context Lab RSS Reader"}
        },
        {
            "id": "api_data",
            "name": "API数据",
            "type": "rest",
            "url": "https://api.example.com/data",
            "method": "GET",
            "headers": {"Authorization": "Bearer ${API_TOKEN}"},
            "params": {"limit": 50},
            "data_path": "data.items",
            "timestamp_field": "updated_at",
            "id_field": "id"
        }
    ]
}
```

### 4. 聊天历史捕获器 (ChatHistoryCapture)

通过MCP接口获取聊天历史，支持按时间范围和用户ID过滤。

**主要特性：**
- 定期轮询聊天历史
- 支持按发送者、聊天ID、消息类型和关键词过滤
- 增量获取消息，避免重复处理
- 自动解析时间戳和消息格式

**配置示例：**
```python
config = {
    "polling_interval": 300.0,  # 轮询间隔（秒）
    "lookback_hours": 24,       # 回溯时间（小时）
    "max_messages_per_poll": 100, # 每次轮询最大获取消息数
    "mcp_config": {
        "endpoint": "https://mcp.example.com/chat/history",
        "headers": {"Authorization": "Bearer ${MCP_TOKEN}"},
        "params": {"user_id": "${USER_ID}"}
    },
    "message_filter": {
        "role_ids": ["user1", "user2"],
        "chat_ids": ["chat1", "chat2"],
        "message_types": ["text", "image"],
        "keywords": ["重要", "紧急"]
    }
}
```

### 5. AI对话捕获器 (AIConversationCapture)

通过MCP接口获取AI对话内容，支持按用户ID和模型过滤。

**主要特性：**
- 定期轮询AI对话
- 支持按用户ID、模型和系统提示词过滤
- 增量获取对话，避免重复处理
- 保留完整的对话上下文

**配置示例：**
```python
config = {
    "polling_interval": 300.0,  # 轮询间隔（秒）
    "lookback_hours": 24,       # 回溯时间（小时）
    "max_conversations_per_poll": 50, # 每次轮询最大获取对话数
    "mcp_config": {
        "endpoint": "https://mcp.example.com/ai/conversations",
        "headers": {"Authorization": "Bearer ${MCP_TOKEN}"},
        "params": {"user_id": "${USER_ID}"}
    },
    "conversation_filter": {
        "user_ids": ["user1", "user2"],
        "models": ["gpt-4", "claude-3"],
        "system_prompt": "你是一个助手"
    }
}
```


## 使用示例

以下是使用上下文捕获模块的简单示例：

```python
from context_lab.context_capture import ScreenshotCapture, FileMonitorCapture

# 创建截图捕获器
screenshot_config = {
    "interval": 5.0,
    "save_path": "./screenshots",
    "deduplication": True,
}
screenshot_capture = ScreenshotCapture(screenshot_config)

# 创建文件监控器
file_monitor_config = {
    "paths": ["./documents"],
    "patterns": ["*.txt", "*.md", "*.pdf"],
    "recursive": True,
}
file_monitor = FileMonitorCapture(file_monitor_config)

# 启动捕获器
screenshot_capture.start()
file_monitor.start()

try:
    # 应用主循环
    while True:
        # 检查截图捕获器
        context = screenshot_capture.capture()
        if context:
            print(f"捕获到截图: {context.id}")
            # 处理上下文...
            
        time.sleep(1)
except KeyboardInterrupt:
    # 停止捕获器
    screenshot_capture.stop()
    file_monitor.stop()
```

更多详细示例请参考 `examples/context_capture_demo.py`。

## 扩展开发

要开发新的捕获器，只需继承 `BaseContextCapture` 基类并实现必要的方法：

```python
from context_lab.context_capture import BaseContextCapture
from context_lab.models.context import Context, ContextSource

class MyCustomCapture(BaseContextCapture):
    def __init__(self, config):
        super().__init__(config)
        # 初始化自定义状态...
        
    def start(self):
        super().start()
        # 启动捕获逻辑...
        
    def stop(self):
        # 停止捕获逻辑...
        super().stop()
        
    def capture(self):
        # 实现捕获逻辑...
        return Context(
            source=ContextSource.OTHER,
            content_type="text/plain",
            content="捕获的内容",
            metadata={"custom_field": "value"}
        )
        
    def get_status(self):
        status = super().get_status()
        status.update({
            # 添加自定义状态...
        })
        return status
```