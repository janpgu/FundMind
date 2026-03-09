import pytest

from fund_mind import Document, pick_best_document

LANG_PREF = ("EN", "DE", "FR", "IT", "ES")


def doc(language, date="2025-01-01", active=True, url="http://example.com/x.pdf"):
    return Document(doc_type="PR", language=language, date=date, active=active, url=url)


class TestPickBestDocument:
    def test_empty_list_returns_none(self):
        assert pick_best_document([], LANG_PREF) is None

    def test_picks_preferred_language(self):
        docs = [doc("FR"), doc("EN"), doc("DE")]
        assert pick_best_document(docs, LANG_PREF).language == "EN"

    def test_falls_back_to_next_preferred(self):
        docs = [doc("FR"), doc("DE")]
        assert pick_best_document(docs, LANG_PREF).language == "DE"

    def test_falls_back_to_any_language_if_none_preferred(self):
        docs = [doc("JA"), doc("ZH")]
        result = pick_best_document(docs, LANG_PREF)
        assert result is not None
        assert result.language in ("JA", "ZH")

    def test_active_preferred_over_inactive(self):
        docs = [
            doc("EN", date="2025-06-01", active=False),
            doc("EN", date="2020-01-01", active=True),
        ]
        assert pick_best_document(docs, LANG_PREF).active is True

    def test_most_recent_active_wins(self):
        docs = [
            doc("EN", date="2024-01-01", active=True),
            doc("EN", date="2025-06-01", active=True),
            doc("EN", date="2023-01-01", active=True),
        ]
        assert pick_best_document(docs, LANG_PREF).date == "2025-06-01"

    def test_inactive_fallback_picks_most_recent(self):
        docs = [
            doc("EN", date="2023-01-01", active=False),
            doc("EN", date="2025-06-01", active=False),
        ]
        assert pick_best_document(docs, LANG_PREF).date == "2025-06-01"

    def test_active_language_preferred_over_inactive_better_language(self):
        docs = [
            doc("EN", active=False),
            doc("DE", active=True),
        ]
        # Active DE beats inactive EN because active docs are prioritised first
        assert pick_best_document(docs, LANG_PREF).language == "DE"

    def test_case_insensitive_language_matching(self):
        docs = [doc("en")]
        assert pick_best_document(docs, LANG_PREF).language == "en"
