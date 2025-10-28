# -*- coding: utf-8 -*-

# crawl_utils/services/items_normalizer.py

"""
ItemsNormalizer - Merge, Explode, Transform (Simplified v2)

Simplified Architecture (Step 8 Refactoring):
1. **Merge**: extracted_records (runtime) < preset_item_policy (policy)
   - Priority: preset takes precedence over extracted data
   - No override logic here (handled in SyncCrawl)
2. **Explode**: Convert field arrays to individual items
   - List[value]  Multiple CrawlItem instances
3. **Transform**: Apply ItemNormalizer to each CrawlItem
   - Validation: Pydantic model validation
   - Type conversion: str  int, float, etc.
"""

from typing import Dict, List, Any, Optional
import logging

from ..core.policy import CrawlItem
from modules.keypath_utils import KeyPathDict
from .item_normalizer import ItemNormalizer


__all__ = ["ItemsNormalizer"]


logger = logging.getLogger(__name__)


class ItemsNormalizer:
    """
    ItemsNormalizer - Merge, Explode, Transform (Simplified)
    
    Responsibilities:
    - Merge: extracted_records < preset_item_policy (policy priority)
    - Explode: List[value]  Multiple CrawlItem instances
    - Transform: Apply ItemNormalizer for validation/conversion
    
    Changes from v1:
    -  Removed: split_flat_overrides_by_item_prefix()
    -  Removed: OverrideProcessor integration
    -  Removed: KeyPathState usage
    -  Added: Simple merge (preset > extracted)
    -  Added: _transform_single_value() helper
    """
    
    def __init__(
        self,
        log: Optional[Any] = None  # ✅ Accept Any logger (loguru or logging)
    ):
        """
        Initialize ItemsNormalizer.
        
        Args:
            log: Logger instance (optional, loguru or logging compatible)
        """
        self.normalizer = ItemNormalizer()
        self.log = log or logger
    
    def process(
        self,
        extracted_records: Any,
        preset_item_policy: Optional[KeyPathDict] = None
    ) -> List[CrawlItem]:
        """
        Process extractor output into List[CrawlItem].
        
        NEW Architecture (v3):
        Step 1: Normalize extracted_records to List[flat_dict] (support multiple records)
        Step 2: Build preset policies by KeyPath (source field)
        Step 3: For each record:
                  For each preset policy:
                    - Extract data from record using KeyPath
                    - Explode arrays if needed
                    - Create CrawlItem with policy + data + indices
        
        Args:
            extracted_records: Flattened KeyPath dict or List[dict] (single or multiple records)
            preset_item_policy: KeyPathDict with preset policies (optional)
        
        Returns:
            List[CrawlItem]: Normalized items with record_index and item_index set
        """
        self.log.info(f"[ItemsNormalizer] Starting process (preset_item_policy: {preset_item_policy is not None})")
        
        # Step 1: Normalize to List[flat_dict] (support multiple records)
        records: List[Dict[str, Any]] = []
        if isinstance(extracted_records, list):
            if len(extracted_records) == 0:
                self.log.warning(f"[ItemsNormalizer] Empty extracted_records")
                return []
            records = extracted_records
        elif isinstance(extracted_records, dict):
            records = [extracted_records]
        else:
            self.log.warning(f"[ItemsNormalizer] Invalid extracted_records type: {type(extracted_records)}")
            return []
        
        self.log.info(f"[ItemsNormalizer] Step 1: Processing {len(records)} record(s)")
        
        # Step 2: Extract preset policies
        preset_policies: Dict[str, Dict[str, Any]] = {}
        if preset_item_policy:
            preset_policies = preset_item_policy.data
            self.log.info(f"[ItemsNormalizer] Step 2: {len(preset_policies)} preset policies")
        else:
            self.log.debug(f"[ItemsNormalizer] Step 2: No preset policies")
        
        # Step 3: Process each record -> each preset policy
        result_items: List[CrawlItem] = []
        
        for record_idx, record in enumerate(records):
            self.log.debug(f"[ItemsNormalizer] Processing record {record_idx + 1}/{len(records)} with {len(record)} fields")
            
            for keypath, policy in preset_policies.items():
                self.log.debug(f"[ItemsNormalizer]   Processing preset: {keypath}")
                
                # Extract source KeyPath from policy
                source_keypath = policy.get('source', keypath)
                
                # Extract data from record using KeyPath
                data_values = record.get(source_keypath)
                
                if data_values is None:
                    self.log.debug(f"[ItemsNormalizer]   No data for KeyPath: {source_keypath}")
                    continue
                
                # Normalize to list
                if not isinstance(data_values, list):
                    data_values = [data_values]
                
                self.log.debug(f"[ItemsNormalizer]   {keypath}: processing {len(data_values)} values")
                
                # Create CrawlItem for each value
                for item_idx, value in enumerate(data_values):
                    try:
                        # Transform using ItemNormalizer
                        # source는 실제 데이터 (URL or bytes), policy_like는 정책 메타데이터
                        crawl_item = self.normalizer.normalize(
                            source=value,  # Runtime data (URL or bytes)
                            policy_like=policy
                        )
                        
                        # Set runtime indices (CrawlItem expects these to be set by ItemsNormalizer)
                        crawl_item.record_index = record_idx  # 0-based record index
                        crawl_item.item_index = item_idx + 1  # 1-based item index per policy per record
                        
                        result_items.append(crawl_item)
                        
                        self.log.debug(f"[ItemsNormalizer]   ✅ Created CrawlItem (record={record_idx}, item={item_idx + 1})")
                        
                    except Exception as e:
                        self.log.error(f"[ItemsNormalizer]   ❌ Failed to create CrawlItem: {e}")
                        import traceback
                        self.log.debug(traceback.format_exc())
        
        self.log.info(f"[ItemsNormalizer] ✅ Completed: {len(result_items)} items created")
        return result_items
