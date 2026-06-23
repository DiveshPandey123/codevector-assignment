import base64
import json
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class PaginationCursor:
    last_product_id: str
    last_updated_at: datetime
    snapshot_version: int
    
    def encode(self) -> str:
        cursor_dict = {
            'id': self.last_product_id,
            'updated_at': self.last_updated_at.isoformat(),
            'snap': self.snapshot_version,
        }
        json_str = json.dumps(cursor_dict)
        return base64.b64encode(json_str.encode()).decode('utf-8')
    
    @staticmethod
    def decode(cursor_str: str) -> 'PaginationCursor':
        try:
            json_str = base64.b64decode(cursor_str.encode()).decode('utf-8')
            data = json.loads(json_str)
            
            return PaginationCursor(
                last_product_id=data['id'],
                last_updated_at=datetime.fromisoformat(data['updated_at']),
                snapshot_version=data['snap'],
            )
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            logger.error(f"Failed to decode cursor: {e}")
            raise ValueError(f"Invalid cursor format: {str(e)}")
