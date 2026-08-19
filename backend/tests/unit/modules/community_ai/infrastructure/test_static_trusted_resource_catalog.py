"""Unit tests for `StaticTrustedResourceCatalog`."""

from app.modules.community_ai.infrastructure.resources.static_trusted_resource_catalog import (
    StaticTrustedResourceCatalog,
)


class TestListSources:
    async def test_returns_the_full_catalog_when_no_keywords_are_given(self) -> None:
        catalog = StaticTrustedResourceCatalog()
        sources = await catalog.list_sources()
        assert len(sources) >= 5
        assert all(source.url.startswith("https://") for source in sources)

    async def test_ranks_by_topic_tag_overlap(self) -> None:
        catalog = StaticTrustedResourceCatalog()
        sources = await catalog.list_sources(keywords=("vaccination",))
        assert sources
        assert sources[0].title == "Centers for Disease Control and Prevention (CDC)"

    async def test_falls_back_to_the_full_catalog_when_no_keyword_matches(self) -> None:
        catalog = StaticTrustedResourceCatalog()
        full = await catalog.list_sources()
        no_match = await catalog.list_sources(keywords=("no-such-topic-xyz",))
        assert {s.url for s in no_match} == {s.url for s in full}

    async def test_never_fabricates_a_source_every_url_is_from_a_real_organization(self) -> None:
        catalog = StaticTrustedResourceCatalog()
        sources = await catalog.list_sources()
        known_domains = {
            "medlineplus.gov",
            "cdc.gov",
            "who.int",
            "mayoclinic.org",
            "cochranelibrary.com",
            "ncbi.nlm.nih.gov",
        }
        for source in sources:
            assert any(domain in source.url for domain in known_domains)
