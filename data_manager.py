import sqlite3
import pandas as pd
import os
import logging
from typing import List, Optional

from config import DB_PATH, INSTRUMENT_CONFIG, LEGACY_DATASET_ID, TFF_DATASET_ID
from cftc_api import fetch_all_historical_data, normalize_legacy_data, normalize_tff_data

logger = logging.getLogger(__name__)

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Initializes the database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Table for normalized COT data
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cot_data (
        Date TEXT,
        Contract_Code TEXT,
        Report_Type TEXT,
        Open_Interest REAL,
        Comm_Long REAL,
        Comm_Short REAL,
        Comm_Net REAL,
        Large_Spec_Long REAL,
        Large_Spec_Short REAL,
        Large_Spec_Net REAL,
        Small_Spec_Long REAL,
        Small_Spec_Short REAL,
        Small_Spec_Net REAL,
        Asset_Mgr_Net REAL,
        Other_Rept_Net REAL,
        PRIMARY KEY (Date, Contract_Code)
    )
    ''')
    conn.commit()
    conn.close()

def load_data_from_db(contract_code: Optional[str] = None) -> pd.DataFrame:
    """Loads normalized data from SQLite into a DataFrame."""
    conn = get_connection()
    query = "SELECT * FROM cot_data"
    
    if contract_code:
        query += f" WHERE Contract_Code = '{contract_code}'"
        
    query += " ORDER BY Date DESC"
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        
    return df

def save_data_to_db(df: pd.DataFrame):
    """Saves normalized data to SQLite, replacing existing on conflict."""
    if df.empty:
        return
        
    conn = get_connection()
    
    # Convert datetime to string for sqlite
    df_save = df.copy()
    df_save['Date'] = df_save['Date'].dt.strftime('%Y-%m-%d')
    
    df_save.to_sql('cot_data', conn, if_exists='append', index=False, 
                   method=lambda table, conn, keys, data_iter: 
                   sqlite_upsert(table, conn, keys, data_iter))
    conn.close()

def sqlite_upsert(table, conn, keys, data_iter):
    """Helper to perform UPSERT (INSERT OR REPLACE) in SQLite."""
    from sqlite3 import IntegrityError
    
    # In some pandas versions, conn here is actually a cursor
    if hasattr(conn, 'cursor'):
        cursor = conn.cursor()
    else:
        cursor = conn
        
    cols = ",".join(keys)
    placeholders = ",".join(["?"] * len(keys))
    
    sql = f"INSERT OR REPLACE INTO {table.name} ({cols}) VALUES ({placeholders})"
    
    for row in data_iter:
        cursor.execute(sql, row)

def update_cache():
    """
    Fetches all historical data from the API for all configured instruments
    and saves it to the SQLite database.
    (For production, we should only fetch records newer than the max date in DB).
    """
    logger.info("Starting cache update...")
    init_db()
    
    # Gather codes
    legacy_codes = []
    tff_codes = []
    
    for name, config in INSTRUMENT_CONFIG.items():
        if not config["cot_available"]:
            continue
        if config["report_type"] == "legacy":
            legacy_codes.append(config["code"])
        elif config["report_type"] == "tff":
            tff_codes.append(config["code"])
            
    # Fetch and process Legacy
    if legacy_codes:
        logger.info(f"Fetching Legacy data for {len(legacy_codes)} contracts...")
        df_legacy = fetch_all_historical_data(LEGACY_DATASET_ID, legacy_codes)
        df_legacy_norm = normalize_legacy_data(df_legacy)
        save_data_to_db(df_legacy_norm)
        
    # Fetch and process TFF
    if tff_codes:
        logger.info(f"Fetching TFF data for {len(tff_codes)} contracts...")
        df_tff = fetch_all_historical_data(TFF_DATASET_ID, tff_codes)
        df_tff_norm = normalize_tff_data(df_tff)
        save_data_to_db(df_tff_norm)
        
    logger.info("Cache update complete!")

def calculate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates derived metrics like % of Open Interest, Z-scores, and WoW changes.
    Assumes df is sorted by Date DESC for a single contract.
    """
    if df.empty:
        return df
        
    df = df.copy()
    
    # Sort chronologically for rolling window calculations
    df = df.sort_values('Date', ascending=True).reset_index(drop=True)
    
    # Calculate % of Open Interest
    df['Comm_Net_Pct_OI'] = (df['Comm_Net'] / df['Open_Interest']) * 100
    df['Large_Spec_Net_Pct_OI'] = (df['Large_Spec_Net'] / df['Open_Interest']) * 100
    
    # Calculate WoW changes
    df['Comm_Net_WoW'] = df['Comm_Net'].diff()
    df['Large_Spec_Net_WoW'] = df['Large_Spec_Net'].diff()
    
    # Calculate Z-scores (3-year rolling = 156 weeks)
    window = 156 
    df['Comm_Net_ZScore_3Y'] = (df['Comm_Net'] - df['Comm_Net'].rolling(window).mean()) / df['Comm_Net'].rolling(window).std()
    df['Large_Spec_Net_ZScore_3Y'] = (df['Large_Spec_Net'] - df['Large_Spec_Net'].rolling(window).mean()) / df['Large_Spec_Net'].rolling(window).std()
    
    # Re-sort descending (newest first)
    df = df.sort_values('Date', ascending=False).reset_index(drop=True)
    
    return df

def get_processed_data(contract_code: str) -> pd.DataFrame:
    """Convenience method to load and process data for a single contract."""
    df = load_data_from_db(contract_code)
    return calculate_metrics(df)
