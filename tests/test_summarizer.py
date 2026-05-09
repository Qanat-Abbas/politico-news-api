from app.summarizer import summarize


def test_summarize_prefers_keyword_sentences() -> None:
    text = (
        "Weather reports mentioned scattered rain across the region. "
        "Technology companies announced new artificial intelligence tools for hospitals. "
        "The technology rollout is expected to change patient scheduling and diagnosis workflows. "
        "Sports teams played late games across several cities. "
        "Analysts said technology adoption will depend on privacy safeguards."
    )

    summary = summarize(text, "technology", max_sentences=2)

    assert "Technology companies" in summary
    assert summary.lower().count("technology") >= 2
    assert "Weather reports" not in summary
    assert "Sports teams" not in summary


def test_summarize_empty_text_has_fallback() -> None:
    assert summarize("", "anything") == "No readable article text was available to summarize."
