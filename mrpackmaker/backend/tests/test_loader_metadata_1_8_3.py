import asyncio
import json

import pytest

from app.models.enums import LoaderType
from app.services.loader_metadata import LoaderMetadataError, OfficialLoaderResolver


def run(coro):
    return asyncio.run(coro)


def test_fabric_meta_resolves_015_loader():
    async def exercise():
        async def fetch(url):
            assert url.endswith('/1.20.1')
            return json.dumps([{'loader': {'version': '0.15.11', 'stable': True}}, {'loader': {'version': '0.15.10', 'stable': True}}])

        result = await OfficialLoaderResolver(fetch).resolve(LoaderType.FABRIC, '1.20.1')
        assert result.version == '0.15.11'
        assert result.source == 'fabric-meta'

    run(exercise())


def test_forge_maven_resolves_472():
    async def exercise():
        async def fetch(url):
            assert 'maven.minecraftforge.net' in url
            return '<metadata><versioning><versions><version>1.20.1-47.2.0</version><version>1.20.1-47.1.0</version><version>1.20.2-48.0.0</version></versions></versioning></metadata>'

        result = await OfficialLoaderResolver(fetch).resolve(LoaderType.FORGE, '1.20.1')
        assert result.version == '47.2.0'
        assert result.source == 'forge-maven'

    run(exercise())


def test_neoforge_maven_uses_official_source():
    async def exercise():
        async def fetch(url):
            assert 'maven.neoforged.net' in url
            return '<metadata><versioning><versions><version>20.4.237</version><version>20.4.200</version></versions></versioning></metadata>'

        result = await OfficialLoaderResolver(fetch).resolve(LoaderType.NEOFORGE, '1.20.4')
        assert result.version == '20.4.237'
        assert result.source == 'neoforge-maven'

    run(exercise())


def test_empty_metadata_is_a_typed_resolution_error():
    async def exercise():
        async def fetch(url):
            return '<metadata><versioning><versions /></versioning></metadata>'

        with pytest.raises(LoaderMetadataError, match='No forge version found'):
            await OfficialLoaderResolver(fetch).resolve(LoaderType.FORGE, '1.20.1')

    run(exercise())


def test_incompatible_requested_version_is_rejected():
    async def exercise():
        async def fetch(url):
            return '<metadata><versioning><versions><version>1.20.1-47.2.0</version></versions></versioning></metadata>'

        with pytest.raises(LoaderMetadataError):
            await OfficialLoaderResolver(fetch).resolve(LoaderType.FORGE, '1.20.1', '47.0.0')

    run(exercise())
