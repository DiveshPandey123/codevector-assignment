"""Tests for pagination logic and consistency."""
import pytest
from datetime import datetime
from app.pagination import PaginationCursor
import json
import base64


class TestPaginationCursor:
    """Test cursor encoding and decoding."""
    
    def test_cursor_encoding_roundtrip(self):
        """Test that cursor can be encoded and decoded without loss."""
        # Arrange
        cursor = PaginationCursor(
            last_product_id="prod_123",
            last_updated_at=datetime(2024, 1, 15, 10, 30, 0),
            snapshot_version=42,
        )
        
        # Act
        encoded = cursor.encode()
        decoded = PaginationCursor.decode(encoded)
        
        # Assert
        assert decoded.last_product_id == cursor.last_product_id
        assert decoded.last_updated_at == cursor.last_updated_at
        assert decoded.snapshot_version == cursor.snapshot_version
    
    def test_cursor_is_base64(self):
        """Test that cursor encodes to valid base64."""
        cursor = PaginationCursor(
            last_product_id="prod_xyz",
            last_updated_at=datetime(2024, 1, 1, 0, 0, 0),
            snapshot_version=1,
        )
        
        encoded = cursor.encode()
        
        # Should be valid base64
        try:
            decoded_json = base64.b64decode(encoded).decode('utf-8')
            data = json.loads(decoded_json)
            assert data['id'] == 'prod_xyz'
            assert data['snap'] == 1
        except Exception as e:
            pytest.fail(f"Cursor is not valid base64: {e}")
    
    def test_cursor_invalid_format_raises_error(self):
        """Test that invalid cursor raises ValueError."""
        with pytest.raises(ValueError):
            PaginationCursor.decode("not-valid-base64!!!")
    
    def test_cursor_malformed_json_raises_error(self):
        """Test that malformed JSON in cursor raises ValueError."""
        malformed = base64.b64encode(b"not json").decode()
        with pytest.raises(ValueError):
            PaginationCursor.decode(malformed)
    
    def test_cursor_missing_fields_raises_error(self):
        """Test that cursor missing required fields raises ValueError."""
        incomplete_data = json.dumps({"id": "prod_123"})
        malformed = base64.b64encode(incomplete_data.encode()).decode()
        with pytest.raises(ValueError):
            PaginationCursor.decode(malformed)
