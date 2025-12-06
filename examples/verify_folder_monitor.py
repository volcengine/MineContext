import os
import shutil
import tempfile
import time
import logging
from unittest.mock import MagicMock, patch

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
# 确保能看到 opencontext 的日志
logging.getLogger("opencontext").setLevel(logging.INFO)
logger = logging.getLogger("FolderMonitorVerifier")

# 模拟 Storage
mock_storage = MagicMock()
# 默认返回空，但在删除测试前我们会修改它
mock_storage.get_all_processed_contexts.return_value = {}
mock_storage.delete_processed_context.return_value = True


# 定义一个简单的 Mock Context 对象
class MockContext:
    def __init__(self, ctx_id):
        self.id = ctx_id


@patch("opencontext.context_capture.folder_monitor.get_storage", return_value=mock_storage)
def run_verification(mock_get_storage):
    from opencontext.context_capture.folder_monitor import FolderMonitorCapture
    from opencontext.models.enums import ContextType

    # 创建临时目录
    temp_dir = tempfile.mkdtemp(prefix="test_monitor_")
    logger.info(f"Created temporary watch directory: {temp_dir}")

    monitor = None
    try:
        # 初始化 FolderMonitorCapture
        monitor = FolderMonitorCapture()

        config = {
            "monitor_interval": 1,
            "watch_folder_paths": [temp_dir],
            "recursive": True,
            "max_file_size": 1024 * 1024,
            "initial_scan": True,
        }

        logger.info("--- Step 1: Initialization ---")
        if not monitor.initialize(config):
            logger.error("❌ Initialization failed!")
            return

        # 启动监控
        monitor.start()
        time.sleep(1)
        logger.info("✅ Monitor started")

        # 4. 测试场景：创建文件
        logger.info("\n--- Step 2: Test File Creation ---")
        test_file_1 = os.path.join(temp_dir, "test1.txt")
        with open(test_file_1, "w", encoding="utf-8") as f:
            f.write("Hello World")

        logger.info(f"Created file: {os.path.basename(test_file_1)}")
        time.sleep(1)

        results = monitor.capture()

        # 验证创建
        if len(results) == 1 and results[0].additional_info.get("event_type") == "file_created":
            logger.info(
                f"✅ PASS: Captured 'file_created' event. Content: {results[0].content_text}"
            )
        else:
            logger.error(f"❌ FAIL: Expected 1 creation event, got {len(results)}")

        # 5. 测试场景：修改文件
        logger.info("\n--- Step 3: Test File Update ---")
        with open(test_file_1, "a", encoding="utf-8") as f:
            f.write("\nUpdated Content")

        logger.info(f"Updated file: {os.path.basename(test_file_1)}")
        time.sleep(1)

        results = monitor.capture()

        # 验证修改
        if len(results) == 1 and results[0].additional_info.get("event_type") == "file_updated":
            logger.info(f"✅ PASS: Captured 'file_updated' event.")
        else:
            logger.error(f"❌ FAIL: Expected 1 update event, got {len(results)}")

        # 6. 测试场景：删除文件
        logger.info("\n--- Step 4: Test File Deletion ---")

        # 关键点：在删除前，配置 mock storage 返回模拟的 Context 数据
        # 这样 FolderMonitor 才会去尝试删除它们
        mock_storage.get_all_processed_contexts.return_value = {
            ContextType.KNOWLEDGE_CONTEXT: [
                MockContext("mock_ctx_id_1"),
                MockContext("mock_ctx_id_2"),
            ]
        }

        os.remove(test_file_1)
        logger.info(f"Deleted file: {os.path.basename(test_file_1)}")

        time.sleep(1)

        # 执行capture，触发cleanup
        results = monitor.capture()

        if len(results) == 0:
            logger.info("✅ PASS: Capture returned 0 events for deletion (as expected).")
        else:
            logger.error(f"❌ FAIL: Expected 0 events for deletion, got {len(results)}")

        # 验证内部副作用：检查 Storage 的 delete 方法是否被调用
        # 模拟了返回 2 个 context，所以应该调用 2 次 delete
        delete_call_count = mock_storage.delete_processed_context.call_count
        if delete_call_count >= 2:
            logger.info(
                f"✅ PASS: Storage cleanup triggered. 'delete_processed_context' called {delete_call_count} times."
            )
            # 验证调用参数中是否包含我们的 mock id
            calls = mock_storage.delete_processed_context.call_args_list
            ids_deleted = [call.kwargs.get("id") or call.args[0] for call in calls]
            logger.info(f"   -> Deleted Context IDs: {ids_deleted}")
        else:
            logger.error(f"❌ FAIL: Storage cleanup NOT triggered. Call count: {delete_call_count}")

        # 7. 停止监控
        logger.info("\n--- Step 5: Cleanup ---")
        monitor.stop()

    finally:
        if monitor:
            monitor.stop()
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")


if __name__ == "__main__":
    import sys

    sys.path.append(os.getcwd())

    try:
        run_verification()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
