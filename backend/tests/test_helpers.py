"""测试 sales_twin _helpers 模块中的核心工具函数"""

from datetime import date

from app.api.sales_twin._helpers import (
    _extract_json_object,
    _parse_date,
    _allowed_attachment,
    _parse_pagination_params,
)


# ===== _extract_json_object =====
class TestExtractJsonObject:
    def test_pure_json_string(self):
        result = _extract_json_object('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_in_code_block(self):
        result = _extract_json_object('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_with_code_block_no_language(self):
        result = _extract_json_object('```\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_with_surrounding_text(self):
        result = _extract_json_object('这是结果：{"key": "value"} 以上。')
        assert result == {"key": "value"}

    def test_invalid_json_returns_none(self):
        assert _extract_json_object('{"key": value}') is None

    def test_no_braces_returns_none(self):
        assert _extract_json_object('not json at all') is None

    def test_empty_input_returns_none(self):
        assert _extract_json_object('') is None

    def test_none_input_returns_none(self):
        assert _extract_json_object(None) is None

    def test_nested_json(self):
        result = _extract_json_object('{"a": {"b": [1, 2]}}')
        assert result == {"a": {"b": [1, 2]}}


# ===== _parse_date =====
class TestParseDate:
    def test_valid_date_string(self):
        result = _parse_date('2026-07-23')
        assert result == date(2026, 7, 23)

    def test_invalid_date_string_returns_none(self):
        assert _parse_date('not-a-date') is None

    def test_empty_string_returns_none(self):
        assert _parse_date('') is None

    def test_none_returns_none(self):
        assert _parse_date(None) is None

    def test_null_string_returns_none(self):
        assert _parse_date('null') is None

    def test_date_object_passthrough(self):
        d = date(2026, 7, 23)
        assert _parse_date(d) is d

    def test_datetime_string_truncated_to_date(self):
        result = _parse_date('2026-07-23T10:30:00')
        assert result == date(2026, 7, 23)


# ===== _allowed_attachment =====
class TestAllowedAttachment:
    def test_valid_extension_returns_true(self):
        assert _allowed_attachment('file.pdf') is True

    def test_valid_extension_uppercase(self):
        assert _allowed_attachment('file.PDF') is True

    def test_invalid_extension_returns_false(self):
        assert _allowed_attachment('file.exe') is False

    def test_no_extension_returns_false(self):
        assert _allowed_attachment('filename') is False

    def test_empty_filename_returns_false(self):
        assert _allowed_attachment('') is False

    def test_none_returns_false(self):
        assert _allowed_attachment(None) is False


# ===== _parse_pagination_params =====
class TestParsePaginationParams:
    def test_default_values(self, app):
        with app.test_request_context('/'):
            page, per_page = _parse_pagination_params()
            assert page == 1
            assert per_page == 20  # DEFAULT_PER_PAGE

    def test_custom_values(self, app):
        with app.test_request_context('/?page=3&per_page=50'):
            page, per_page = _parse_pagination_params()
            assert page == 3
            assert per_page == 50

    def test_page_below_minimum_clamped_to_1(self, app):
        with app.test_request_context('/?page=0&per_page=50'):
            page, per_page = _parse_pagination_params()
            assert page == 1

    def test_per_page_above_max_clamped_to_100(self, app):
        with app.test_request_context('/?page=1&per_page=200'):
            page, per_page = _parse_pagination_params()
            assert per_page == 100  # MAX_PER_PAGE

    def test_negative_values_clamped(self, app):
        with app.test_request_context('/?page=-5&per_page=-10'):
            page, per_page = _parse_pagination_params()
            assert page == 1
            assert per_page == 1
