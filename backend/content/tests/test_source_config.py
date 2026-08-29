import pytest

from content.source_config import SourceConfigError, load_sources_file


def test_load_sources_file(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text(
        """
apiVersion: content-tracker/v1
sources:
  - key: example-podcast
    adapter: podcast
    config:
      feed_url: https://example.org/feed.xml
""".strip(),
        encoding="utf-8",
    )

    document = load_sources_file(path)

    assert document.sources[0].key == "example-podcast"
    assert document.sources[0].adapter == "podcast"
    assert document.sources[0].config["feed_url"] == "https://example.org/feed.xml"


def test_duplicate_source_keys_are_rejected(tmp_path):
    path = tmp_path / "sources.yaml"
    path.write_text(
        """
apiVersion: content-tracker/v1
sources:
  - key: duplicate
    adapter: podcast
  - key: duplicate
    adapter: podcast
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(SourceConfigError, match="duplicate source keys"):
        load_sources_file(path)
