"""Property-based tests using hypothesis."""
import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta
from decimal import Decimal
from app.pagination import PaginationCursor
import json
import base64


# Custom strategies
product_id_strategy = st.text(
    alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_",
    min_size=5,
    max_size=20,
).filter(lambda x: x and not x.startswith('_'))

datetime_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2025, 12, 31),
    timezones=None,  # Use naive datetimes
)

snapshot_version_strategy = st.integers(min_value=0, max_value=2**31 - 1)


class TestPaginationCursorProperties:
    """Property-based tests for pagination cursor."""
    
    @given(
        product_id=product_id_strategy,
        updated_at=datetime_strategy,
        snapshot_version=snapshot_version_strategy,
    )
    @settings(max_examples=100)
    def test_cursor_roundtrip_preserves_all_fields(
        self, product_id, updated_at, snapshot_version
    ):
        """
        Property: For any cursor state, encoding and decoding preserves all fields.
        
        Validates: Design Property 3 - Cursor Encoding Round Trip
        """
        # Arrange
        original = PaginationCursor(
            last_product_id=product_id,
            last_updated_at=updated_at,
            snapshot_version=snapshot_version,
        )
        
        # Act
        encoded = original.encode()
        decoded = PaginationCursor.decode(encoded)
        
        # Assert
        assert decoded.last_product_id == original.last_product_id
        assert decoded.last_updated_at == original.last_updated_at
        assert decoded.snapshot_version == original.snapshot_version
    
    @given(
        product_id=product_id_strategy,
        updated_at=datetime_strategy,
        snapshot_version=snapshot_version_strategy,
    )
    @settings(max_examples=100)
    def test_cursor_encoding_is_valid_base64(
        self, product_id, updated_at, snapshot_version
    ):
        """
        Property: Cursor encoding always produces valid base64.
        
        Validates: Design Property 3 - Cursor Encoding Round Trip
        """
        cursor = PaginationCursor(
            last_product_id=product_id,
            last_updated_at=updated_at,
            snapshot_version=snapshot_version,
        )
        
        # Act
        encoded = cursor.encode()
        
        # Assert - should not raise
        decoded_json = base64.b64decode(encoded).decode('utf-8')
        data = json.loads(decoded_json)
        
        assert data['id'] == product_id
        assert data['snap'] == snapshot_version
    
    @given(
        product_id=product_id_strategy,
        updated_at=datetime_strategy,
        snapshot_version=snapshot_version_strategy,
    )
    @settings(max_examples=100)
    def test_cursor_encode_decode_idempotent(
        self, product_id, updated_at, snapshot_version
    ):
        """
        Property: Encoding a cursor multiple times produces same result.
        
        Validates: Design Property 3 - Cursor Encoding Round Trip
        """
        cursor = PaginationCursor(
            last_product_id=product_id,
            last_updated_at=updated_at,
            snapshot_version=snapshot_version,
        )
        
        # Act
        encoded1 = cursor.encode()
        encoded2 = cursor.encode()
        
        # Assert
        assert encoded1 == encoded2


class TestCursorComparison:
    """Property-based tests for cursor ordering."""
    
    @given(
        cursor1_id=product_id_strategy,
        cursor1_time=datetime_strategy,
        cursor2_id=product_id_strategy,
        cursor2_time=datetime_strategy,
    )
    @settings(max_examples=100)
    def test_cursor_field_extraction_consistency(
        self, cursor1_id, cursor1_time, cursor2_id, cursor2_time
    ):
        """
        Property: Cursor fields can be extracted consistently regardless of other values.
        
        Validates: Design Property 3 - Cursor Encoding Round Trip
        """
        cursor1 = PaginationCursor(
            last_product_id=cursor1_id,
            last_updated_at=cursor1_time,
            snapshot_version=42,
        )
        cursor2 = PaginationCursor(
            last_product_id=cursor2_id,
            last_updated_at=cursor2_time,
            snapshot_version=99,
        )
        
        # Act
        decoded1 = PaginationCursor.decode(cursor1.encode())
        decoded2 = PaginationCursor.decode(cursor2.encode())
        
        # Assert
        assert decoded1.last_product_id == cursor1.last_product_id
        assert decoded1.last_updated_at == cursor1.last_updated_at
        assert decoded2.last_product_id == cursor2.last_product_id
        assert decoded2.last_updated_at == cursor2.last_updated_at
        # Different snapshots
        assert decoded1.snapshot_version != decoded2.snapshot_version


class TestTimeComparisonProperties:
    """Property-based tests for timestamp handling."""
    
    @given(
        datetime1=datetime_strategy,
        datetime2=datetime_strategy,
    )
    @settings(max_examples=100)
    def test_datetime_ordering_preserved_in_cursor(
        self, datetime1, datetime2
    ):
        """
        Property: DateTime ordering is preserved when encoded in cursor.
        
        Validates: Design Property 1 - Sort Order Consistency
        """
        cursor1 = PaginationCursor(
            last_product_id="prod_1",
            last_updated_at=datetime1,
            snapshot_version=1,
        )
        cursor2 = PaginationCursor(
            last_product_id="prod_2",
            last_updated_at=datetime2,
            snapshot_version=1,
        )
        
        # Act
        decoded1 = PaginationCursor.decode(cursor1.encode())
        decoded2 = PaginationCursor.decode(cursor2.encode())
        
        # Assert - ordering preserved
        if datetime1 < datetime2:
            assert decoded1.last_updated_at < decoded2.last_updated_at
        elif datetime1 > datetime2:
            assert decoded1.last_updated_at > decoded2.last_updated_at
        else:
            assert decoded1.last_updated_at == decoded2.last_updated_at


class TestSnapshotVersionProperties:
    """Property-based tests for snapshot version handling."""
    
    @given(
        snap_versions=st.lists(
            snapshot_version_strategy,
            min_size=1,
            max_size=100,
            unique=True,
        )
    )
    @settings(max_examples=50)
    def test_snapshot_versions_unique_preserved(self, snap_versions):
        """
        Property: Different snapshot versions remain distinct after encoding/decoding.
        
        Validates: Design Property 6 & 7 - Snapshot Isolation
        """
        cursors = [
            PaginationCursor(
                last_product_id=f"prod_{i}",
                last_updated_at=datetime(2024, 1, 1),
                snapshot_version=snap_versions[i],
            )
            for i in range(len(snap_versions))
        ]
        
        # Act
        decoded_cursors = [
            PaginationCursor.decode(c.encode())
            for c in cursors
        ]
        decoded_versions = [c.snapshot_version for c in decoded_cursors]
        
        # Assert
        assert len(set(decoded_versions)) == len(snap_versions)
