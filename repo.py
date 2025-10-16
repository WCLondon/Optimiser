"""
Repository layer for BNG Optimiser reference/config tables.
Reads all reference data from Supabase Postgres tables via SQLAlchemy Core.
All table names and column names match the Excel tab names exactly.
"""

import streamlit as st
import pandas as pd
from sqlalchemy import text, MetaData, Table
from typing import Dict, Optional
import logging

from db import DatabaseConnection

logger = logging.getLogger(__name__)


@st.cache_resource
def get_db_engine():
    """
    Get the SQLAlchemy engine for database connections.
    Cached as a resource to reuse across app reruns.
    
    Returns:
        SQLAlchemy Engine instance
    """
    return DatabaseConnection.get_engine()


@st.cache_data(ttl=600)
def fetch_banks() -> pd.DataFrame:
    """
    Fetch Banks reference table from Supabase.
    
    Expected columns:
        - bank_id: str
        - bank_name: str
        - lpa_name: str (optional)
        - nca_name: str (optional)
        - postcode: str (optional)
        - address: str (optional)
        - lat: float (optional)
        - lon: float (optional)
    
    Returns:
        DataFrame with Banks data
    """
    engine = get_db_engine()
    query = "SELECT * FROM \"Banks\""
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        logger.error(f"Error fetching Banks table: {e}")
        raise RuntimeError(f"Failed to fetch Banks table from database: {e}")


@st.cache_data(ttl=600)
def fetch_pricing() -> pd.DataFrame:
    """
    Fetch Pricing reference table from Supabase.
    
    Expected columns:
        - bank_id: str
        - habitat_name: str
        - contract_size: str
        - tier: str
        - price (or unit_price, Unit Price, etc.): float
        - broader_type: str (optional)
        - distinctiveness_name: str (optional)
    
    Returns:
        DataFrame with Pricing data
    """
    engine = get_db_engine()
    query = "SELECT * FROM \"Pricing\""
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        logger.error(f"Error fetching Pricing table: {e}")
        raise RuntimeError(f"Failed to fetch Pricing table from database: {e}")


@st.cache_data(ttl=600)
def fetch_habitat_catalog() -> pd.DataFrame:
    """
    Fetch HabitatCatalog reference table from Supabase.
    
    Expected columns:
        - habitat_name: str
        - broader_type: str
        - distinctiveness_name: str
        - UmbrellaType: str (optional - "area", "hedgerow", "watercourse")
    
    Returns:
        DataFrame with HabitatCatalog data
    """
    engine = get_db_engine()
    query = "SELECT * FROM \"HabitatCatalog\""
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        logger.error(f"Error fetching HabitatCatalog table: {e}")
        raise RuntimeError(f"Failed to fetch HabitatCatalog table from database: {e}")


@st.cache_data(ttl=600)
def fetch_stock() -> pd.DataFrame:
    """
    Fetch Stock reference table from Supabase.
    
    Expected columns:
        - bank_id: str
        - habitat_name: str
        - stock_id: str
        - quantity_available: float (or available_excl_quotes, quoted, etc.)
    
    Returns:
        DataFrame with Stock data
    """
    engine = get_db_engine()
    query = "SELECT * FROM \"Stock\""
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        logger.error(f"Error fetching Stock table: {e}")
        raise RuntimeError(f"Failed to fetch Stock table from database: {e}")


@st.cache_data(ttl=600)
def fetch_distinctiveness_levels() -> pd.DataFrame:
    """
    Fetch DistinctivenessLevels reference table from Supabase.
    
    Expected columns:
        - distinctiveness_name: str
        - level_value: float
    
    Returns:
        DataFrame with DistinctivenessLevels data
    """
    engine = get_db_engine()
    query = "SELECT * FROM \"DistinctivenessLevels\""
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        logger.error(f"Error fetching DistinctivenessLevels table: {e}")
        raise RuntimeError(f"Failed to fetch DistinctivenessLevels table from database: {e}")


@st.cache_data(ttl=600)
def fetch_srm() -> pd.DataFrame:
    """
    Fetch SRM (Strategic Resource Multipliers) reference table from Supabase.
    
    Expected columns:
        - tier: str (e.g., "local", "adjacent", "far")
        - multiplier: float
    
    Returns:
        DataFrame with SRM data
    """
    engine = get_db_engine()
    query = "SELECT * FROM \"SRM\""
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        logger.error(f"Error fetching SRM table: {e}")
        raise RuntimeError(f"Failed to fetch SRM table from database: {e}")


@st.cache_data(ttl=600)
def fetch_trading_rules() -> pd.DataFrame:
    """
    Fetch TradingRules reference table from Supabase (optional).
    
    Returns:
        DataFrame with TradingRules data, or empty DataFrame if table doesn't exist
    """
    engine = get_db_engine()
    query = "SELECT * FROM \"TradingRules\""
    
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        logger.warning(f"TradingRules table not found or error: {e}")
        # Return empty DataFrame if table doesn't exist (optional table)
        return pd.DataFrame()


def fetch_all_reference_tables() -> Dict[str, pd.DataFrame]:
    """
    Fetch all reference/config tables from Supabase.
    
    Returns:
        Dictionary with table names as keys and DataFrames as values.
        Matches the structure previously loaded from Excel:
        {
            "Banks": DataFrame,
            "Pricing": DataFrame,
            "HabitatCatalog": DataFrame,
            "Stock": DataFrame,
            "DistinctivenessLevels": DataFrame,
            "SRM": DataFrame,
            "TradingRules": DataFrame (optional)
        }
    """
    return {
        "Banks": fetch_banks(),
        "Pricing": fetch_pricing(),
        "HabitatCatalog": fetch_habitat_catalog(),
        "Stock": fetch_stock(),
        "DistinctivenessLevels": fetch_distinctiveness_levels(),
        "SRM": fetch_srm(),
        "TradingRules": fetch_trading_rules()
    }


def check_required_tables_not_empty() -> Dict[str, bool]:
    """
    Check if required reference tables exist and are not empty.
    Used by Admin Dashboard to show warnings.
    
    Returns:
        Dictionary with table names as keys and boolean values indicating if table is non-empty
    """
    required_tables = [
        "Banks",
        "Pricing",
        "HabitatCatalog",
        "Stock",
        "DistinctivenessLevels",
        "SRM"
    ]
    
    status = {}
    
    for table_name in required_tables:
        try:
            if table_name == "Banks":
                df = fetch_banks()
            elif table_name == "Pricing":
                df = fetch_pricing()
            elif table_name == "HabitatCatalog":
                df = fetch_habitat_catalog()
            elif table_name == "Stock":
                df = fetch_stock()
            elif table_name == "DistinctivenessLevels":
                df = fetch_distinctiveness_levels()
            elif table_name == "SRM":
                df = fetch_srm()
            else:
                df = pd.DataFrame()
            
            status[table_name] = not df.empty
        except Exception as e:
            logger.error(f"Error checking table {table_name}: {e}")
            status[table_name] = False
    
    return status


def validate_reference_tables() -> tuple[bool, list[str]]:
    """
    Validate that all required reference tables exist and have data.
    
    Returns:
        Tuple of (all_valid: bool, errors: list[str])
    """
    errors = []
    
    try:
        status = check_required_tables_not_empty()
        
        for table_name, is_valid in status.items():
            if not is_valid:
                errors.append(f"{table_name} table is empty or missing")
        
        return (len(errors) == 0, errors)
    
    except Exception as e:
        errors.append(f"Failed to validate reference tables: {e}")
        return (False, errors)
