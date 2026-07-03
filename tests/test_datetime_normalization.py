import importlib.util
import sys
import tempfile
import threading
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class DummyLogger:
    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


class FlexibleModel:
    _counter = 0

    def __init__(self, **kwargs):
        if "id" not in kwargs:
            FlexibleModel._counter += 1
            kwargs["id"] = f"obj-{FlexibleModel._counter}"
        self.__dict__.update(kwargs)


def ensure_package(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module
    return module


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def install_base_stubs():
    for package_name in [
        "opencontext",
        "opencontext.utils",
        "opencontext.models",
        "opencontext.storage",
        "opencontext.server",
        "opencontext.context_capture",
        "opencontext.context_processing",
        "opencontext.context_processing.processor",
        "opencontext.llm",
        "opencontext.monitoring",
        "opencontext.tools",
        "opencontext.config",
    ]:
        ensure_package(package_name)

    logging_utils = types.ModuleType("opencontext.utils.logging_utils")
    logging_utils.get_logger = lambda _name: DummyLogger()
    sys.modules["opencontext.utils.logging_utils"] = logging_utils

    models_context = types.ModuleType("opencontext.models.context")
    models_context.RawContextProperties = FlexibleModel
    models_context.ContextProperties = FlexibleModel
    models_context.ExtractedData = FlexibleModel
    models_context.Vectorize = FlexibleModel
    models_context.ProcessedContext = FlexibleModel
    sys.modules["opencontext.models.context"] = models_context

    enum_like = lambda value: types.SimpleNamespace(value=value)
    models_enums = types.ModuleType("opencontext.models.enums")
    models_enums.ContentFormat = types.SimpleNamespace(IMAGE="image", FILE="file", TEXT="text")
    models_enums.ContextSource = types.SimpleNamespace(
        SCREENSHOT="screenshot",
        LOCAL_FILE="local_file",
        TEXT="text",
        VAULT="vault",
    )
    models_enums.ContextType = types.SimpleNamespace(ACTIVITY_CONTEXT=enum_like("activity_context"))
    models_enums.get_context_type_options = lambda: []
    models_enums.get_context_type_descriptions_for_extraction = lambda: ""
    models_enums.get_context_type_for_analysis = lambda value: enum_like(value)
    sys.modules["opencontext.models.enums"] = models_enums

    models_context.ContextSource = models_enums.ContextSource
    models_context.ContentFormat = models_enums.ContentFormat

    global_storage = types.ModuleType("opencontext.storage.global_storage")
    global_storage.get_storage = lambda: None
    sys.modules["opencontext.storage.global_storage"] = global_storage

    return models_context, models_enums


def load_datetime_utils():
    install_base_stubs()
    return load_module(
        "opencontext.utils.datetime_utils",
        REPO_ROOT / "opencontext" / "utils" / "datetime_utils.py",
    )


def load_context_operations_module():
    install_base_stubs()
    load_datetime_utils()
    return load_module(
        "tests_context_operations",
        REPO_ROOT / "opencontext" / "server" / "context_operations.py",
    )


def load_vault_monitor_module():
    install_base_stubs()
    load_datetime_utils()

    context_capture = types.ModuleType("opencontext.context_capture")

    class BaseCaptureComponent:
        def __init__(self, name: str, description: str, source_type: str):
            self._name = name
            self._description = description
            self._source_type = source_type
            self._config = {}
            self._callback = None

    context_capture.BaseCaptureComponent = BaseCaptureComponent
    sys.modules["opencontext.context_capture"] = context_capture

    return load_module(
        "tests_vault_document_monitor",
        REPO_ROOT / "opencontext" / "context_capture" / "vault_document_monitor.py",
    )


def load_screenshot_processor_module():
    _, models_enums = install_base_stubs()
    load_datetime_utils()

    base_processor = types.ModuleType("opencontext.context_processing.processor.base_processor")

    class BaseContextProcessor:
        def __init__(self, config):
            self.config = config

    base_processor.BaseContextProcessor = BaseContextProcessor
    sys.modules["opencontext.context_processing.processor.base_processor"] = base_processor

    entity_processor = types.ModuleType("opencontext.context_processing.processor.entity_processor")
    entity_processor.refresh_entities = lambda *args, **kwargs: None
    entity_processor.validate_and_clean_entities = lambda entities: entities
    sys.modules["opencontext.context_processing.processor.entity_processor"] = entity_processor

    embedding_client = types.ModuleType("opencontext.llm.global_embedding_client")
    embedding_client.do_vectorize_async = lambda *args, **kwargs: None
    sys.modules["opencontext.llm.global_embedding_client"] = embedding_client

    vlm_client = types.ModuleType("opencontext.llm.global_vlm_client")
    vlm_client.generate_with_messages_async = lambda *args, **kwargs: None
    sys.modules["opencontext.llm.global_vlm_client"] = vlm_client

    monitoring_module = types.ModuleType("opencontext.monitoring")
    monitoring_module.increment_data_count = lambda *args, **kwargs: None
    monitoring_module.increment_recording_stat = lambda *args, **kwargs: None
    monitoring_module.record_processing_metrics = lambda *args, **kwargs: None
    sys.modules["opencontext.monitoring"] = monitoring_module

    monitoring_monitor = types.ModuleType("opencontext.monitoring.monitor")
    monitoring_monitor.record_processing_error = lambda *args, **kwargs: None
    sys.modules["opencontext.monitoring.monitor"] = monitoring_monitor

    tools_module = types.ModuleType("opencontext.tools.tool_definitions")
    tools_module.ALL_TOOL_DEFINITIONS = []
    sys.modules["opencontext.tools.tool_definitions"] = tools_module

    image_module = types.ModuleType("opencontext.utils.image")
    image_module.calculate_phash = lambda *args, **kwargs: "0"
    image_module.resize_image = lambda *args, **kwargs: None
    sys.modules["opencontext.utils.image"] = image_module

    json_parser = types.ModuleType("opencontext.utils.json_parser")
    json_parser.parse_json_from_response = lambda response: response
    sys.modules["opencontext.utils.json_parser"] = json_parser

    config_module = types.ModuleType("opencontext.config.global_config")
    config_module.get_prompt_group = lambda _name: {"system": "", "user": ""}
    config_module.get_config = lambda _name=None: {}
    sys.modules["opencontext.config.global_config"] = config_module

    return load_module(
        "tests_screenshot_processor",
        REPO_ROOT / "opencontext" / "context_processing" / "processor" / "screenshot_processor.py",
    )


class DatetimeNormalizationTests(unittest.TestCase):
    def test_parse_local_datetime_converts_aware_input_to_local_naive(self):
        datetime_utils = load_datetime_utils()

        parsed = datetime_utils.parse_local_datetime("2026-04-03T03:35:38Z")
        expected = (
            datetime(2026, 4, 3, 3, 35, 38, tzinfo=timezone.utc)
            .astimezone(datetime_utils.get_local_timezone())
            .replace(tzinfo=None)
        )

        self.assertEqual(parsed, expected)
        self.assertIsNone(parsed.tzinfo)
        self.assertEqual(
            datetime_utils.parse_local_datetime("2026-04-03 11:35:38"),
            datetime(2026, 4, 3, 11, 35, 38),
        )

    def test_context_operations_add_screenshot_normalizes_iso_timestamp(self):
        datetime_utils = load_datetime_utils()
        module = load_context_operations_module()

        captured = {}

        def callback(raw_context):
            captured["raw_context"] = raw_context
            return True

        with tempfile.NamedTemporaryFile() as tmp_file:
            result = module.ContextOperations().add_screenshot(
                tmp_file.name,
                "screen",
                "2026-04-03T03:35:38Z",
                "window",
                callback,
            )

        self.assertIsNone(result)
        self.assertIn("raw_context", captured)
        expected = datetime_utils.parse_local_datetime("2026-04-03T03:35:38Z")
        self.assertEqual(captured["raw_context"].create_time, expected)
        self.assertIsNone(captured["raw_context"].create_time.tzinfo)

    def test_vault_document_monitor_scans_aware_strings_without_typeerror(self):
        datetime_utils = load_datetime_utils()
        module = load_vault_monitor_module()

        monitor = module.VaultDocumentMonitor()
        monitor._storage = types.SimpleNamespace(
            get_vaults=lambda **kwargs: [
                {
                    "id": 7,
                    "title": "Doc",
                    "summary": "Summary",
                    "content": "Body",
                    "tags": "",
                    "document_type": "Report",
                    "created_at": "2026-04-03T03:35:38Z",
                    "updated_at": "2026-04-03T03:35:38Z",
                }
            ]
        )
        monitor._last_scan_time = datetime_utils.parse_local_datetime("2026-04-03T03:30:00Z")
        monitor._processed_vault_ids = set()
        monitor._document_events = []
        monitor._event_lock = threading.RLock()
        monitor._last_activity_time = None

        monitor._scan_vault_changes()

        self.assertEqual(len(monitor._document_events), 1)
        self.assertIn(7, monitor._processed_vault_ids)
        self.assertIsNone(monitor._document_events[0]["timestamp"].tzinfo)

        context = monitor._create_context_from_event(monitor._document_events[0])
        self.assertEqual(
            context.create_time,
            datetime_utils.parse_local_datetime("2026-04-03T03:35:38Z"),
        )
        self.assertIsNone(context.create_time.tzinfo)

    def test_screenshot_processor_normalizes_event_time_before_comparison(self):
        datetime_utils = load_datetime_utils()
        module = load_screenshot_processor_module()
        models_context = sys.modules["opencontext.models.context"]
        models_enums = sys.modules["opencontext.models.enums"]

        processor = object.__new__(module.ScreenshotProcessor)
        raw_context = models_context.RawContextProperties(
            source=models_enums.ContextSource.SCREENSHOT,
            content_format=models_enums.ContentFormat.IMAGE,
            create_time=datetime(2026, 4, 3, 11, 34, 49),
            content_path="/tmp/fake.png",
            additional_info={},
        )

        context = processor._create_processed_context(
            {
                "context_type": "semantic_context",
                "event_time": "2026-04-03T03:35:38Z",
                "title": "Title",
                "summary": "Summary",
            },
            raw_context,
        )

        expected_event_time = datetime_utils.parse_local_datetime("2026-04-03T03:35:38Z")
        self.assertEqual(context.properties.event_time, expected_event_time)
        self.assertIsNone(context.properties.event_time.tzinfo)
        self.assertLessEqual(context.properties.event_time, datetime(2026, 4, 3, 11, 40, 0))


if __name__ == "__main__":
    unittest.main()
