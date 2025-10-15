# -*- coding: utf-8 -*-
"""Test DataFrame Mixins and DataFrameOps."""

import pandas as pd
from modules.structured_data import DataFrameOps, DFPolicy


def test_clean_mixin():
    """Test CleanMixin operations."""
    print("=" * 60)
    print("TEST: CleanMixin")
    print("=" * 60)
    
    # Create test DataFrame with empty rows/columns
    df = pd.DataFrame({
        'name': ['Alice', 'Bob', None, 'Charlie'],
        'age': [30, None, None, 35],
        'empty_col': [None, None, None, None]
    })
    
    ops = DataFrameOps()
    
    # Test drop_empty
    cleaned = ops.drop_empty_df(df)
    print(f"Original shape: {df.shape}")
    print(f"Cleaned shape: {cleaned.shape}")
    assert 'empty_col' not in cleaned.columns  # Empty column removed
    
    # Test drop_duplicates
    df_dup = pd.DataFrame({
        'name': ['Alice', 'Bob', 'Alice'],
        'age': [30, 25, 30]
    })
    deduped = ops.drop_duplicates_df(df_dup)
    assert len(deduped) == 2  # One duplicate removed
    
    # Test strip_strings
    df_spaces = pd.DataFrame({
        'name': ['  Alice  ', ' Bob', 'Charlie  ']
    })
    stripped = ops.strip_strings_df(df_spaces)
    assert stripped['name'][0] == 'Alice'  # Whitespace stripped
    
    print("✅ CleanMixin works")
    print()


def test_filter_mixin():
    """Test FilterMixin operations."""
    print("=" * 60)
    print("TEST: FilterMixin")
    print("=" * 60)
    
    df = pd.DataFrame({
        'name': ['Alice', 'Bob', 'Charlie', 'David'],
        'age': [30, 25, 35, 28],
        'city': ['Seoul', 'Busan', 'Seoul', 'Incheon']
    })
    
    ops = DataFrameOps()
    
    # Test filter by query
    filtered = ops.filter_df_query(df, "age > 27")
    assert len(filtered) == 3  # Alice, Charlie, David
    
    # Test filter by callable
    filtered2 = ops.filter_df_callable(df, lambda row: row['city'] == 'Seoul')
    assert len(filtered2) == 2  # Alice, Charlie
    
    # Test filter columns
    cols_only = ops.filter_df_columns(df, ['name', 'age'])
    assert list(cols_only.columns) == ['name', 'age']
    
    print("✅ FilterMixin works")
    print()


def test_normalize_mixin():
    """Test NormalizeMixin operations."""
    print("=" * 60)
    print("TEST: NormalizeMixin")
    print("=" * 60)
    
    df = pd.DataFrame({
        'First Name': ['Alice', 'Bob'],
        'Age ': [30, 25],  # Trailing space
        'CITY': ['Seoul', 'Busan']
    })
    
    ops = DataFrameOps()
    
    # Test normalize column names
    normalized = ops.normalize_column_names_df(df)
    expected_cols = ['first_name', 'age', 'city']
    assert list(normalized.columns) == expected_cols
    
    # Test apply to column
    transformed = ops.apply_to_column_df(df, 'Age ', lambda x: x * 2)
    assert transformed['Age '][0] == 60
    
    # Test rename columns
    renamed = ops.rename_columns_df(df, {'First Name': 'name'})
    assert 'name' in renamed.columns
    
    print("✅ NormalizeMixin works")
    print()


def test_from_dict_mixin():
    """Test FromDictMixin operations."""
    print("=" * 60)
    print("TEST: FromDictMixin")
    print("=" * 60)
    
    ops = DataFrameOps()
    
    # Test from_dict_records
    records = [
        {'name': 'Alice', 'age': 30},
        {'name': 'Bob', 'age': 25}
    ]
    df1 = ops.from_dict_records(records)
    assert len(df1) == 2
    assert list(df1.columns) == ['name', 'age']
    
    # Test from_dict_dict
    dict_data = {
        'name': ['Alice', 'Bob'],
        'age': [30, 25]
    }
    df2 = ops.from_dict_dict(dict_data)
    assert len(df2) == 2
    assert list(df2.columns) == ['name', 'age']
    
    # Test from_dict_auto
    df3 = ops.from_dict_auto(records)
    assert len(df3) == 2
    
    print("✅ FromDictMixin works")
    print()


def test_dataframe_ops_composite():
    """Test DataFrameOps composite integration."""
    print("=" * 60)
    print("TEST: DataFrameOps Composite")
    print("=" * 60)
    
    policy = DFPolicy(
        drop_empty_rows=True,
        drop_empty_cols=True,
        normalize_columns=True
    )
    ops = DataFrameOps(policy=policy)
    
    # Create from dict
    data = [
        {'First Name': 'Alice', 'Age': 30, 'City': 'Seoul'},
        {'First Name': 'Bob', 'Age': 25, 'City': 'Busan'},
        {'First Name': 'Charlie', 'Age': 35, 'City': 'Seoul'}
    ]
    df = ops.from_dict_records(data)
    
    # Normalize column names
    df = ops.normalize(df)
    assert 'first_name' in df.columns
    
    # Filter
    df = ops.filter(df, "age > 25")
    assert len(df) == 2  # Alice, Charlie
    
    # Clean
    df = ops.clean(df)
    
    print(f"Final DataFrame shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print("✅ DataFrameOps composite works")
    print()


def test_dataframe_pipeline():
    """Test fluent pipeline interface."""
    print("=" * 60)
    print("TEST: DataFrame Pipeline")
    print("=" * 60)
    
    ops = DataFrameOps()
    
    # Create initial DataFrame
    df = pd.DataFrame({
        'First Name': ['  Alice  ', 'Bob', 'Charlie'],
        'Age ': [30, 25, 35],
        'City': ['Seoul', 'Busan', 'Seoul']
    })
    
    # Use fluent pipeline
    result = ops.pipe(df) \
        .normalize() \
        .clean() \
        .filter("age > 25") \
        .get()
    
    assert len(result) == 2  # Alice, Charlie
    assert 'first_name' in result.columns
    
    print(f"Pipeline result shape: {result.shape}")
    print("✅ Pipeline interface works")
    print()


if __name__ == "__main__":
    test_clean_mixin()
    test_filter_mixin()
    test_normalize_mixin()
    test_from_dict_mixin()
    test_dataframe_ops_composite()
    test_dataframe_pipeline()
    
    print("=" * 60)
    print("ALL DATAFRAME TESTS PASSED ✅")
    print("=" * 60)
