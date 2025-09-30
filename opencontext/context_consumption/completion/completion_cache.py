#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Completion Cache Manager
Provides high-performance caching and optimization for completion results
"""

import hashlib
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class CacheStrategy(Enum):
    """Cache Strategy Enum"""
    LRU = "lru"  # Least Recently Used
    TTL = "ttl"  # Time To Live
    HYBRID = "hybrid"  # Hybrid Strategy


@dataclass
class CacheEntry:
    """Cache Entry"""
    key: str
    suggestions: List[Any]  # Use Any to avoid circular imports
    created_at: datetime
    last_accessed: datetime
    access_count: int
    confidence_score: float
    context_hash: str


class CompletionCache:
    """
    Intelligent Completion Cache Manager
    Supports multiple caching strategies and performance optimizations
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300, 
                 strategy: CacheStrategy = CacheStrategy.HYBRID):
        self.max_size = max_size
        self.ttl = timedelta(seconds=ttl_seconds)
        self.strategy = strategy
        
        # Cache storage
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # LRU order
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'total_requests': 0,
            'average_response_time': 0.0
        }
        
        # Performance optimizations
        self._precomputed_contexts = {}  # Precomputed contexts
        self._hot_keys = set()  # Hot keys
        
        logger.info(f"CompletionCache initialized: max_size={max_size}, ttl={ttl_seconds}s, strategy={strategy.value}")
    
    def get(self, key: str, context_hash: str = None) -> Optional[List[Any]]:
        """Get cached completion suggestions"""
        import time
        start_time = time.time()
        
        with self._lock:
            self._stats['total_requests'] += 1
            
            # Check if key exists
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            entry = self._cache[key]
            
            # Check TTL expiration
            if self._is_expired(entry):
                self._evict(key)
                self._stats['misses'] += 1
                return None
            
            # Check if context matches
            if context_hash and entry.context_hash != context_hash:
                self._stats['misses'] += 1
                return None
            
            # Update access information
            entry.last_accessed = datetime.now()
            entry.access_count += 1
            
            # Update LRU order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            # Mark as hot key
            if entry.access_count > 5:
                self._hot_keys.add(key)
            
            self._stats['hits'] += 1
            
            # Update average response time
            response_time = time.time() - start_time
            self._update_average_response_time(response_time)
            
            logger.debug(f"Cache hit: {key[:20]}...")
            return entry.suggestions
    
    def put(self, key: str, suggestions: List[Any], 
            context_hash: str = None, confidence_score: float = 0.0):
        """Add completion suggestions to the cache"""
        with self._lock:
            now = datetime.now()
            
            # If cache is full, execute eviction policy
            if len(self._cache) >= self.max_size:
                self._evict_entries()
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                suggestions=suggestions,
                created_at=now,
                last_accessed=now,
                access_count=0,
                confidence_score=confidence_score,
                context_hash=context_hash or ""
            )
            
            # Add to cache
            self._cache[key] = entry
            self._access_order.append(key)
            
            logger.debug(f"Cache add: {key[:20]}... ({len(suggestions)} suggestions)")
    
    def invalidate(self, pattern: str = None):
        """Invalidate the cache"""
        with self._lock:
            if pattern is None:
                # Clear all cache
                self._cache.clear()
                self._access_order.clear()
                self._hot_keys.clear()
                logger.info("All cache cleared")
            else:
                # Invalidate by pattern
                keys_to_remove = [key for key in self._cache.keys() if pattern in key]
                for key in keys_to_remove:
                    self._evict(key)
                logger.info(f"Invalidated cache by pattern: {pattern} ({len(keys_to_remove)} items)")
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if a cache entry is expired"""
        if self.strategy in [CacheStrategy.TTL, CacheStrategy.HYBRID]:
            return datetime.now() - entry.created_at > self.ttl
        return False
    
    def _evict_entries(self):
        """Evict cache entries"""
        if self.strategy == CacheStrategy.LRU or self.strategy == CacheStrategy.HYBRID:
            # LRU eviction
            while len(self._cache) >= self.max_size and self._access_order:
                oldest_key = self._access_order[0]
                
                # Protect hot keys
                if oldest_key in self._hot_keys and len(self._cache) < self.max_size * 1.2:
                    # If it's a hot key and there's still space, skip it
                    self._access_order.remove(oldest_key)
                    self._access_order.append(oldest_key)  # Move to the end
                    continue
                
                self._evict(oldest_key)
        
        elif self.strategy == CacheStrategy.TTL:
            # TTL eviction
            now = datetime.now()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now - entry.created_at > self.ttl
            ]
            
            for key in expired_keys:
                self._evict(key)
            
            # If still full after TTL eviction, evict by confidence score
            if len(self._cache) >= self.max_size:
                sorted_entries = sorted(
                    self._cache.items(),
                    key=lambda x: x[1].confidence_score
                )
                
                for key, _ in sorted_entries[:len(self._cache) - self.max_size + 10]:
                    self._evict(key)
    
    def _evict(self, key: str):
        """Evict a single cache entry"""
        if key in self._cache:
            del self._cache[key]
            self._stats['evictions'] += 1
        
        if key in self._access_order:
            self._access_order.remove(key)
        
        if key in self._hot_keys:
            self._hot_keys.remove(key)
    
    def _update_average_response_time(self, response_time: float):
        """Update the average response time"""
        if self._stats['average_response_time'] == 0:
            self._stats['average_response_time'] = response_time
        else:
            # Exponential moving average
            alpha = 0.1
            self._stats['average_response_time'] = (
                alpha * response_time + 
                (1 - alpha) * self._stats['average_response_time']
            )
    
    def precompute_context(self, document_id: int, content: str):
        """Precompute document context"""
        try:
            # Extract key information for precomputation
            lines = content.split('\n')
            
            # Calculate common patterns
            patterns = {
                'headings': [line for line in lines if line.startswith('#')],
                'lists': [line for line in lines if line.strip().startswith(('-', '*', '+'))],
                'code_blocks': [line for line in lines if line.strip().startswith('```')],
                'links': [line for line in lines if '[' in line and '](' in line]
            }
            
            # Generate context hash
            context_data = f"{document_id}:{len(content)}:{len(lines)}"
            context_hash = hashlib.md5(context_data.encode()).hexdigest()
            
            self._precomputed_contexts[document_id] = {
                'hash': context_hash,
                'patterns': patterns,
                'computed_at': datetime.now()
            }
            
            logger.debug(f"Precomputed document context: {document_id}")
            
        except Exception as e:
            logger.error(f"Failed to precompute context: {e}")
    
    def get_precomputed_context(self, document_id: int) -> Optional[Dict[str, Any]]:
        """Get precomputed context"""
        return self._precomputed_contexts.get(document_id)
    
    def optimize(self):
        """Cache optimization"""
        with self._lock:
            # 1. Clean up expired entries
            now = datetime.now()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now - entry.created_at > self.ttl * 2  # Entries older than 2 * TTL
            ]
            
            for key in expired_keys:
                self._evict(key)
            
            # 2. Update hot keys
            self._hot_keys = {
                key for key, entry in self._cache.items()
                if entry.access_count > 3 or key in self._hot_keys
            }
            
            # 3. Compact access order list
            self._access_order = [key for key in self._access_order if key in self._cache]
            
            # 4. Clean up old precomputed contexts
            old_contexts = [
                doc_id for doc_id, ctx in self._precomputed_contexts.items()
                if now - ctx['computed_at'] > timedelta(hours=1)
            ]
            
            for doc_id in old_contexts:
                del self._precomputed_contexts[doc_id]
            
            logger.info(f"Cache optimization complete: cleaned {len(expired_keys)} expired entries, {len(old_contexts)} old contexts")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._stats['total_requests']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'cache_size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate': round(hit_rate, 2),
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'total_requests': total_requests,
                'hot_keys_count': len(self._hot_keys),
                'precomputed_contexts': len(self._precomputed_contexts),
                'average_response_time_ms': round(self._stats['average_response_time'] * 1000, 2),
                'memory_usage_estimate': self._estimate_memory_usage()
            }
    
    def _estimate_memory_usage(self) -> Dict[str, int]:
        """Estimate memory usage"""
        try:
            import sys
            
            cache_size = sys.getsizeof(self._cache)
            for key, entry in self._cache.items():
                cache_size += sys.getsizeof(key)
                cache_size += sys.getsizeof(entry.suggestions)
                for suggestion in entry.suggestions:
                    if hasattr(suggestion, 'text'):
                        cache_size += sys.getsizeof(suggestion.text)
            
            precomputed_size = sys.getsizeof(self._precomputed_contexts)
            for ctx in self._precomputed_contexts.values():
                precomputed_size += sys.getsizeof(ctx)
            
            return {
                'cache_bytes': cache_size,
                'precomputed_bytes': precomputed_size,
                'total_bytes': cache_size + precomputed_size,
                'cache_mb': round(cache_size / 1024 / 1024, 2),
                'total_mb': round((cache_size + precomputed_size) / 1024 / 1024, 2)
            }
        except Exception:
            return {'error': 'Unable to estimate memory usage'}
    
    def export_hot_patterns(self) -> List[Dict[str, Any]]:
        """Export hot patterns for model training optimization"""
        hot_patterns = []
        
        with self._lock:
            for key in self._hot_keys:
                if key in self._cache:
                    entry = self._cache[key]
                    hot_patterns.append({
                        'key_hash': hashlib.md5(key.encode()).hexdigest(),
                        'access_count': entry.access_count,
                        'confidence_score': entry.confidence_score,
                        'suggestion_types': [
                            getattr(s, 'completion_type', {}).get('value', 'unknown') 
                            if hasattr(s, 'completion_type') else 'unknown'
                            for s in entry.suggestions
                        ],
                        'suggestion_count': len(entry.suggestions)
                    })
        
        return hot_patterns


# Global cache instance
_completion_cache_instance = None

def get_completion_cache() -> CompletionCache:
    """Get the global completion cache instance"""
    global _completion_cache_instance
    if _completion_cache_instance is None:
        _completion_cache_instance = CompletionCache()
    return _completion_cache_instance


def clear_completion_cache():
    """Clear the global completion cache"""
    global _completion_cache_instance
    if _completion_cache_instance is not None:
        _completion_cache_instance.invalidate()


# Cache decorator
def cache_completion(ttl: int = 300):
    """
    Completion cache decorator
    
    Args:
        ttl: Cache time-to-live in seconds (not yet implemented, reserved parameter)
    """
    _ = ttl  # Mark parameter as used to avoid warnings
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cache = get_completion_cache()
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # Execute original function
            result = func(*args, **kwargs)
            
            # Cache the result
            if result:
                cache.put(cache_key, result)
            
            return result
        
        return wrapper
    return decorator