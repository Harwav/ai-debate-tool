"""
Unit tests for DebateCache - File-based caching with TTL.

Tests:
1. Cache hit/miss behavior
2. TTL expiration (5 minutes default)
3. Cache invalidation on file changes
"""

import pytest
import tempfile
import time
from pathlib import Path
from datetime import datetime, timedelta
from ai_debate_tool.services.debate_cache import DebateCache


class TestDebateCache:
    """Test suite for DebateCache component."""

    @pytest.fixture
    def cache_dir(self):
        """Create temporary cache directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)

        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def cache(self, cache_dir):
        """Create DebateCache instance with temp directory."""
        return DebateCache(cache_dir=cache_dir, ttl_minutes=5)

    def test_cache_hit_miss(self, cache):
        """Test cache hit and miss behavior."""
        prompt = "Review this refactoring plan"
        file_hash = "abc123"

        # Miss - not cached yet
        result = cache.get(prompt, file_hash)
        assert result is None

        # Cache the response
        response = {'score': 85, 'analysis': 'Good plan'}
        success = cache.set(prompt, response, file_hash)
        assert success is True

        # Hit - should return cached response
        cached = cache.get(prompt, file_hash)
        assert cached is not None
        assert cached['score'] == 85
        assert cached['analysis'] == 'Good plan'

    def test_ttl_expiration(self, cache_dir):
        """Test that cache entries expire after TTL."""
        # Create cache with 1-second TTL for fast testing
        cache = DebateCache(cache_dir=cache_dir, ttl_minutes=0.017)  # ~1 second

        prompt = "Test prompt"
        response = {'data': 'test'}

        # Cache response
        cache.set(prompt, response)

        # Immediate hit
        assert cache.get(prompt) is not None

        # Wait for expiration (2 seconds)
        time.sleep(2)

        # Should be expired (miss)
        result = cache.get(prompt)
        assert result is None

    def test_file_hash_invalidation(self, cache):
        """Test cache invalidation when file hash changes."""
        prompt = "Analyze this file"
        file_hash_v1 = "hash_version_1"
        file_hash_v2 = "hash_version_2"

        # Cache with v1 hash
        response_v1 = {'version': 1}
        cache.set(prompt, response_v1, file_hash_v1)

        # Hit with v1 hash
        cached = cache.get(prompt, file_hash_v1)
        assert cached is not None
        assert cached['version'] == 1

        # Miss with v2 hash (file changed)
        cached_v2 = cache.get(prompt, file_hash_v2)
        assert cached_v2 is None

        # Cache with v2 hash
        response_v2 = {'version': 2}
        cache.set(prompt, response_v2, file_hash_v2)

        # Hit with v2 hash
        cached = cache.get(prompt, file_hash_v2)
        assert cached is not None
        assert cached['version'] == 2

        # v1 hash still returns v1 response (different cache key)
        cached_v1 = cache.get(prompt, file_hash_v1)
        assert cached_v1 is not None
        assert cached_v1['version'] == 1


class TestDebateCacheUtilities:
    """Test cache utility methods."""

    @pytest.fixture
    def cache_dir(self):
        """Create temporary cache directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)

        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def cache(self, cache_dir):
        """Create DebateCache instance."""
        return DebateCache(cache_dir=cache_dir, ttl_minutes=5)

    def test_clear_expired(self, cache_dir):
        """Test clearing expired cache entries."""
        cache = DebateCache(cache_dir=cache_dir, ttl_minutes=0.017)  # 1 second TTL

        # Cache 3 responses
        cache.set("prompt1", {"data": 1})
        cache.set("prompt2", {"data": 2})
        cache.set("prompt3", {"data": 3})

        # All cached
        stats = cache.get_stats()
        assert stats['total_entries'] == 3
        assert stats['valid_entries'] == 3

        # Wait for expiration
        time.sleep(2)

        # Clear expired
        cleared = cache.clear_expired()
        assert cleared == 3

        # All cleared
        stats = cache.get_stats()
        assert stats['total_entries'] == 0

    def test_clear_all(self, cache):
        """Test clearing all cache entries."""
        # Cache 5 responses
        for i in range(5):
            cache.set(f"prompt{i}", {"data": i})

        # Verify cached
        stats = cache.get_stats()
        assert stats['total_entries'] == 5

        # Clear all
        cleared = cache.clear_all()
        assert cleared == 5

        # All cleared
        stats = cache.get_stats()
        assert stats['total_entries'] == 0

    def test_get_stats(self, cache_dir):
        """Test cache statistics."""
        cache = DebateCache(cache_dir=cache_dir, ttl_minutes=0.017)  # 1 second TTL

        # Empty cache
        stats = cache.get_stats()
        assert stats['total_entries'] == 0
        assert stats['valid_entries'] == 0
        assert stats['expired_entries'] == 0

        # Cache 3 responses
        for i in range(3):
            cache.set(f"prompt{i}", {"data": i})

        # All valid
        stats = cache.get_stats()
        assert stats['total_entries'] == 3
        assert stats['valid_entries'] == 3
        assert stats['expired_entries'] == 0

        # Wait for expiration
        time.sleep(2)

        # All expired
        stats = cache.get_stats()
        assert stats['total_entries'] == 3
        assert stats['valid_entries'] == 0
        assert stats['expired_entries'] == 3

    def test_hash_file_content(self):
        """Test file content hashing for cache invalidation."""
        # Create temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write("Original content")
            temp_path = f.name

        try:
            # Hash original
            hash1 = DebateCache.hash_file_content(temp_path)
            assert len(hash1) == 16  # MD5 hex (first 16 chars)

            # Modify file
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write("Modified content")

            # Hash should change
            hash2 = DebateCache.hash_file_content(temp_path)
            assert hash2 != hash1

            # Same content = same hash
            hash3 = DebateCache.hash_file_content(temp_path)
            assert hash3 == hash2
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestDebateCacheEdgeCases:
    """Test edge cases for DebateCache."""

    @pytest.fixture
    def cache_dir(self):
        """Create temporary cache directory."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)

        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_corrupted_cache_file(self, cache_dir):
        """Test handling corrupted cache file."""
        cache = DebateCache(cache_dir=cache_dir)

        # Create corrupted cache file manually
        cache_file = cache_dir / "corrupted.json"
        cache_file.write_text("{ invalid json }", encoding='utf-8')

        # Should handle gracefully (return None)
        # (In real implementation, uses _generate_cache_key, but this tests file handling)
        stats = cache.get_stats()  # Should not crash
        assert stats is not None

    def test_nonexistent_file_hash(self):
        """Test hashing nonexistent file."""
        hash_result = DebateCache.hash_file_content("nonexistent_file.txt")

        # Should return some hash (timestamp-based fallback)
        assert len(hash_result) == 16


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
