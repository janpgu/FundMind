from datetime import datetime

import pytest

from fund_mind import make_output_filename, parse_date, sanitize_filename_part


class TestParseDate:
    def test_iso_date(self):
        assert parse_date("2025-10-13") == datetime(2025, 10, 13)

    def test_iso_datetime(self):
        assert parse_date("2025-10-13T00:00:00") == datetime(2025, 10, 13)

    def test_iso_datetime_with_ms(self):
        assert parse_date("2025-10-13T12:34:56.789") == datetime(2025, 10, 13, 12, 34, 56, 789000)

    def test_dot_format(self):
        assert parse_date("13.10.2025") == datetime(2025, 10, 13)

    def test_slash_format(self):
        assert parse_date("13/10/2025") == datetime(2025, 10, 13)

    def test_empty_string_returns_min(self):
        assert parse_date("") == datetime.min

    def test_garbage_returns_min(self):
        assert parse_date("not-a-date") == datetime.min


class TestSanitizeFilenamePart:
    def test_plain_string_unchanged(self):
        assert sanitize_filename_part("CH0002788708") == "CH0002788708"

    def test_spaces_replaced_with_underscore(self):
        assert sanitize_filename_part("hello world") == "hello_world"

    def test_forbidden_chars_replaced(self):
        assert sanitize_filename_part('a/b:c"d') == "a_b_c_d"

    def test_leading_trailing_dots_stripped(self):
        assert sanitize_filename_part("...foo...") == "foo"

    def test_empty_returns_unknown(self):
        assert sanitize_filename_part("") == "unknown"

    def test_none_like_empty_returns_unknown(self):
        assert sanitize_filename_part(None) == "unknown"


class TestMakeOutputFilename:
    def test_standard_case(self):
        result = make_output_filename("CH0002788708", "PR", "EN", "2025-10-13")
        assert result == "CH0002788708_PR_EN_2025-10-13.pdf"

    def test_missing_language_uses_xx(self):
        result = make_output_filename("IE00BF4RFH31", "AR", "", "2025-01-01")
        assert result == "IE00BF4RFH31_AR_XX_2025-01-01.pdf"

    def test_missing_date_uses_unknown_date(self):
        result = make_output_filename("IE00BF4RFH31", "AR", "DE", "")
        assert result == "IE00BF4RFH31_AR_DE_unknown_date.pdf"

    def test_special_chars_in_isin_sanitized(self):
        result = make_output_filename("IE00/BAD", "PR", "EN", "2025-01-01")
        assert result == "IE00_BAD_PR_EN_2025-01-01.pdf"
