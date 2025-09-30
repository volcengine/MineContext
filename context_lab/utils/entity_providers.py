#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
External entity provider module
Provides integration interfaces for various external entity libraries
"""

import os
import json
import time
import logging
import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import threading
from functools import lru_cache
from collections import OrderedDict

logger = logging.getLogger(__name__)


class LRUCache:
    """Thread-safe LRU cache implementation"""
    
    def __init__(self, maxsize: int = 1000, ttl: int = 3600):
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()
        self.access_times: Dict[str, float] = {}
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        with self.lock:
            if key not in self.cache:
                return None
            
            # Check if expired
            if time.time() - self.access_times[key] > self.ttl:
                del self.cache[key]
                del self.access_times[key]
                return None
            
            # Move to end (most recently used)
            value = self.cache[key]
            del self.cache[key]
            self.cache[key] = value
            self.access_times[key] = time.time()
            
            return value
    
    def set(self, key: str, value: Any):
        """Set cached value"""
        with self.lock:
            current_time = time.time()
            
            if key in self.cache:
                # Update existing key
                del self.cache[key]
            elif len(self.cache) >= self.maxsize:
                # Remove least recently used item
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
            
            self.cache[key] = value
            self.access_times[key] = current_time
    
    def clear(self):
        """Clear cache"""
        with self.lock:
            self.cache.clear()
            self.access_times.clear()
    
    def size(self) -> int:
        """Get current cache size"""
        return len(self.cache)
    
    def cleanup_expired(self):
        """Clean up expired items"""
        with self.lock:
            current_time = time.time()
            expired_keys = []
            
            for key, access_time in self.access_times.items():
                if current_time - access_time > self.ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
                del self.access_times[key]
            
            return len(expired_keys)


@dataclass
class EntityInfo:
    """Entity information structure"""
    entity_canonical_name: str
    entity_aliases: List[str]
    entity_type: Optional[str] = None
    confidence: float = 1.0
    source: str = "unknown"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseEntityProvider(ABC):
    """Entity provider base class"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
        self.timeout = self.config.get('timeout', 10)
        
        # Use LRU cache instead of simple dictionary
        cache_config = self.config.get('cache', {})
        maxsize = cache_config.get('maxsize', 1000)
        ttl = cache_config.get('ttl', self.config.get('cache_ttl', 3600))
        
        self.cache = LRUCache(maxsize=maxsize, ttl=ttl)
        self.last_cleanup = time.time()
        
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name"""
        pass
    
    @abstractmethod
    def search_entities(self, query: str, limit: int = 10) -> List[EntityInfo]:
        """Search entities"""
        pass
    
    @abstractmethod
    def get_entity_info(self, entity_id: str) -> Optional[EntityInfo]:
        """Get specific entity information"""
        pass
    
    def is_available(self) -> bool:
        """Check if provider is available"""
        return self.enabled
    
    def _get_cached(self, cache_key: str) -> Optional[Any]:
        """Get cached data"""
        return self.cache.get(cache_key)
    
    def _set_cache(self, cache_key: str, data: Any):
        """Set cached data"""
        self.cache.set(cache_key, data)
        
        # Periodically clean expired cache
        if time.time() - self.last_cleanup > 3600:  # Clean every hour
            self._cleanup_cache()
    
    def _cleanup_cache(self):
        """Clean expired cache"""
        expired_count = self.cache.cleanup_expired()
        self.last_cleanup = time.time()
        if expired_count > 0:
            logger.debug(f"{self.get_provider_name()}: Cleaned {expired_count} expired cache items")


class SpacyWikidataProvider(BaseEntityProvider):
    """spaCy + Wikidata entity provider"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.nlp = None
        self.entity_linker = None
        self._init_spacy()
    
    def _init_spacy(self):
        """Initialize spaCy and entity linker"""
        if not self.enabled:
            return
            
        try:
            import spacy
            from spacy_entity_linker import EntityLinker
            
            # Check if model is installed
            model_name = self.config.get('model', 'en_core_web_sm')
            if not spacy.util.is_package(model_name):
                logger.warning(f"spaCy model {model_name} not installed, disabling spaCy provider")
                self.enabled = False
                return
            
            self.nlp = spacy.load(model_name)
            self.nlp.add_pipe("entity_linker", last=True)
            logger.info(f"Loaded spaCy model: {model_name}")
            
        except ImportError as e:
            logger.warning(f"spaCy related packages not installed: {e}, disabling spaCy provider")
            self.enabled = False
        except Exception as e:
            logger.error(f"spaCy initialization failed: {e}, disabling spaCy provider")
            self.enabled = False
    
    def get_provider_name(self) -> str:
        return "spacy_wikidata"
    
    def search_entities(self, query: str, limit: int = 10) -> List[EntityInfo]:
        """Search entities using spaCy NER"""
        if not self.enabled or not self.nlp:
            return []
        
        cache_key = f"search_{query}_{limit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        try:
            doc = self.nlp(query)
            entities = []
            
            for ent in doc.ents[:limit]:
                # Get Wikidata link information
                wikidata_id = None
                if hasattr(ent._, 'entity_id'):
                    wikidata_id = ent._.entity_id
                
                entity_info = EntityInfo(
                    entity_canonical_name=ent.text,
                    entity_aliases=[ent.text, ent.lemma_] if hasattr(ent, 'lemma_') else [ent.text],
                    entity_type=ent.label_,
                    confidence=0.8,
                    source=self.get_provider_name(),
                    metadata={
                        'wikidata_id': wikidata_id,
                        'start': ent.start,
                        'end': ent.end,
                        'spacy_label': ent.label_
                    }
                )
                entities.append(entity_info)
            
            self._set_cache(cache_key, entities)
            return entities
            
        except Exception as e:
            logger.error(f"spaCy entity search failed: {e}")
            return []
    
    def get_entity_info(self, entity_id: str) -> Optional[EntityInfo]:
        """Get Wikidata entity information"""
        if not self.enabled:
            return None
        
        cache_key = f"entity_{entity_id}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        # Wikidata API call can be implemented here to get detailed information
        # Temporarily return basic information
        entity_info = EntityInfo(
            entity_canonical_name=entity_id,
            entity_aliases=[entity_id],
            source=self.get_provider_name(),
            metadata={'wikidata_id': entity_id}
        )
        
        self._set_cache(cache_key, entity_info)
        return entity_info


class ConceptNetProvider(BaseEntityProvider):
    """ConceptNet API entity provider"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.api_base = self.config.get('api_base', 'https://api.conceptnet.io')
        self.session = requests.Session()
        self.session.timeout = self.timeout
        self.rate_limit = self.config.get('rate_limit', 0.1)  # 100ms interval
        self.last_request_time = 0
        self._lock = threading.Lock()
    
    def get_provider_name(self) -> str:
        return "conceptnet"
    
    def search_entities(self, query: str, limit: int = 10) -> List[EntityInfo]:
        """Search entities using ConceptNet API"""
        if not self.enabled:
            return []
        
        cache_key = f"search_{query}_{limit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        try:
            # Rate limit
            self._rate_limit()
            
            # Search related concepts
            url = f"{self.api_base}/query"
            params = {
                'node': f'/c/en/{query.lower().replace(" ", "_")}',
                'limit': limit * 2  # Get more and then filter
            }
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            entities = []
            
            seen_concepts = set()
            for edge in data.get('edges', []):
                # Extract related concepts
                start_concept = edge.get('start', {}).get('label', '')
                end_concept = edge.get('end', {}).get('label', '')
                relation = edge.get('rel', {}).get('label', '')
                
                for concept in [start_concept, end_concept]:
                    if concept and concept.lower() != query.lower() and concept not in seen_concepts:
                        entity_info = EntityInfo(
                            entity_canonical_name=concept,
                            entity_aliases=[concept],
                            entity_type=self._map_conceptnet_relation(relation),
                            confidence=edge.get('weight', 1.0),
                            source=self.get_provider_name(),
                            metadata={
                                'relation': relation,
                                'conceptnet_uri': edge.get('start', {}).get('@id') if concept == start_concept else edge.get('end', {}).get('@id')
                            }
                        )
                        entities.append(entity_info)
                        seen_concepts.add(concept)
                        
                        if len(entities) >= limit:
                            break
                
                if len(entities) >= limit:
                    break
            
            self._set_cache(cache_key, entities)
            return entities
            
        except Exception as e:
            logger.error(f"ConceptNet search failed: {e}")
            return []
    
    def get_entity_info(self, entity_id: str) -> Optional[EntityInfo]:
        """Get detailed ConceptNet entity information"""
        if not self.enabled:
            return None
        
        cache_key = f"entity_{entity_id}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        try:
            self._rate_limit()
            
            url = f"{self.api_base}/c/en/{entity_id}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            entity_info = EntityInfo(
                entity_canonical_name=data.get('label', entity_id),
                entity_aliases=[data.get('label', entity_id)],
                source=self.get_provider_name(),
                metadata={
                    'conceptnet_uri': data.get('@id'),
                    'definition': data.get('definition', ''),
                    'language': data.get('@language', 'en')
                }
            )
            
            self._set_cache(cache_key, entity_info)
            return entity_info
            
        except Exception as e:
            logger.error(f"ConceptNet entity information retrieval failed: {e}")
            return None
    
    def _rate_limit(self):
        """Implement rate limiting"""
        with self._lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.rate_limit:
                time.sleep(self.rate_limit - time_since_last)
            self.last_request_time = time.time()
    
    def _map_conceptnet_relation(self, relation: str) -> str:
        """Map ConceptNet relation to entity type"""
        relation_mapping = {
            'IsA': 'concept',
            'PartOf': 'component',
            'UsedFor': 'tool',
            'AtLocation': 'location',
            'CreatedBy': 'person',
            'HasProperty': 'attribute',
            'SimilarTo': 'concept'
        }
        return relation_mapping.get(relation, 'concept')


class EntityProviderManager:
    """Entity provider manager"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.providers: List[BaseEntityProvider] = []
        self._init_providers()
    
    def _init_providers(self):
        """Initialize all providers"""
        # spaCy + Wikidata provider
        spacy_config = self.config.get('spacy', {})
        if spacy_config.get('enabled', False):
            provider = SpacyWikidataProvider(spacy_config)
            if provider.is_available():
                self.providers.append(provider)
                logger.info("Enabled spaCy + Wikidata entity provider")
        
        # ConceptNet provider
        conceptnet_config = self.config.get('conceptnet', {})
        if conceptnet_config.get('enabled', False):
            provider = ConceptNetProvider(conceptnet_config)
            if provider.is_available():
                self.providers.append(provider)
                logger.info("Enabled ConceptNet entity provider")
        
        logger.info(f"Initialized {len(self.providers)} entity providers")
    
    def search_entities(self, query: str, limit: int = 10, timeout: float = 5.0) -> List[EntityInfo]:
        """Search all providers in parallel"""
        if not self.providers:
            return []
        
        all_entities = []
        
        # Query all providers in parallel
        with ThreadPoolExecutor(max_workers=len(self.providers)) as executor:
            futures = []
            for provider in self.providers:
                future = executor.submit(provider.search_entities, query, limit)
                futures.append((provider.get_provider_name(), future))
            
            for provider_name, future in futures:
                try:
                    entities = future.result(timeout=timeout)
                    all_entities.extend(entities)
                    logger.debug(f"{provider_name} returned {len(entities)} entities")
                except FutureTimeoutError:
                    logger.warning(f"{provider_name} query timed out")
                except Exception as e:
                    logger.error(f"{provider_name} query failed: {e}")
        
        # Deduplicate and sort
        unique_entities = self._deduplicate_entities(all_entities)
        return sorted(unique_entities, key=lambda x: x.confidence, reverse=True)[:limit]
    
    def get_entity_info(self, entity_id: str, provider_name: str = None) -> Optional[EntityInfo]:
        """Get entity information from a specific or all providers"""
        if provider_name:
            # Find specific provider
            for provider in self.providers:
                if provider.get_provider_name() == provider_name:
                    return provider.get_entity_info(entity_id)
            return None
        
        # Try all providers
        for provider in self.providers:
            try:
                entity_info = provider.get_entity_info(entity_id)
                if entity_info:
                    return entity_info
            except Exception as e:
                logger.debug(f"{provider.get_provider_name()} failed to get entity info: {e}")
        
        return None
    
    def _deduplicate_entities(self, entities: List[EntityInfo]) -> List[EntityInfo]:
        """Deduplicate entity list"""
        seen = set()
        unique_entities = []
        
        for entity in entities:
            # Use normalized name as deduplication key
            key = entity.entity_canonical_name.lower().strip()
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        return unique_entities
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return [provider.get_provider_name() for provider in self.providers if provider.is_available()]