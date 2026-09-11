import requests
import pandas as pd
from typing import List, Dict, Optional
import logging

from config import API_BASE_URL, LEGACY_DATASET_ID, TFF_DATASET_ID

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_cftc_data(dataset_id: str, contract_codes: List[str], limit: int = 5000, offset: int = 0) -> pd.DataFrame:
    """
    Fetches historical data from the CFTC Socrata API for the given contract codes.
    
    Args:
        dataset_id: The Socrata dataset ID (e.g., legacy or tff).
        contract_codes: List of CFTC contract market codes.
        limit: Number of records to return per request.
        offset: Offset for pagination.
        
    Returns:
        pd.DataFrame containing the fetched data.
    """
    url = f"{API_BASE_URL}{dataset_id}.json"
    
    # Construct SoQL query parameters
    codes_str = ",".join([f"'{code}'" for code in contract_codes])
    
    params = {
        "$where": f"cftc_contract_market_code in({codes_str})",
        "$limit": limit,
        "$offset": offset,
        "$order": "report_date_as_yyyy_mm_dd DESC"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return pd.DataFrame()
            
        return pd.DataFrame(data)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from CFTC API: {e}")
        return pd.DataFrame()

def fetch_all_historical_data(dataset_id: str, contract_codes: List[str]) -> pd.DataFrame:
    """
    Paginates through the API to fetch all historical data for the given codes.
    """
    all_data = []
    limit = 5000
    offset = 0
    
    while True:
        logger.info(f"Fetching {dataset_id} data, offset {offset}...")
        df = fetch_cftc_data(dataset_id, contract_codes, limit=limit, offset=offset)
        
        if df.empty:
            break
            
        all_data.append(df)
        
        if len(df) < limit:
            # Reached the end of the results
            break
            
        offset += limit
        
    if not all_data:
        return pd.DataFrame()
        
    return pd.concat(all_data, ignore_index=True)

def normalize_legacy_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes the Legacy COT data fields into a standard format.
    """
    if df.empty:
        return df
        
    # Standardize column types
    numeric_cols = [
        'comm_positions_long_all', 'comm_positions_short_all',
        'noncomm_positions_long_all', 'noncomm_positions_short_all',
        'nonrept_positions_long_all', 'nonrept_positions_short_all',
        'open_interest_all'
    ]
    
    # Ensure columns exist, fill missing with 0
    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    df['report_date_as_yyyy_mm_dd'] = pd.to_datetime(df['report_date_as_yyyy_mm_dd'])
    
    # Rename to standardized format for the dashboard
    normalized_df = pd.DataFrame({
        'Date': df['report_date_as_yyyy_mm_dd'],
        'Contract_Code': df['cftc_contract_market_code'],
        'Report_Type': 'legacy',
        'Open_Interest': df['open_interest_all'],
        
        # Commercials (Dealers/Hedgers)
        'Comm_Long': df['comm_positions_long_all'],
        'Comm_Short': df['comm_positions_short_all'],
        'Comm_Net': df['comm_positions_long_all'] - df['comm_positions_short_all'],
        
        # Large Specs (Non-Commercial)
        'Large_Spec_Long': df['noncomm_positions_long_all'],
        'Large_Spec_Short': df['noncomm_positions_short_all'],
        'Large_Spec_Net': df['noncomm_positions_long_all'] - df['noncomm_positions_short_all'],
        
        # Small Specs (Non-Reportable)
        'Small_Spec_Long': df['nonrept_positions_long_all'],
        'Small_Spec_Short': df['nonrept_positions_short_all'],
        'Small_Spec_Net': df['nonrept_positions_long_all'] - df['nonrept_positions_short_all'],
    })
    
    return normalized_df

def normalize_tff_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes the TFF (Financial) COT data fields into a standard format.
    """
    if df.empty:
        return df
        
    numeric_cols = [
        'dealer_positions_long_all', 'dealer_positions_short_all',
        'asset_mgr_positions_long', 'asset_mgr_positions_short',
        'lev_money_positions_long', 'lev_money_positions_short',
        'other_rept_positions_long', 'other_rept_positions_short',
        'nonrept_positions_long_all', 'nonrept_positions_short_all',
        'open_interest_all'
    ]
    
    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    df['report_date_as_yyyy_mm_dd'] = pd.to_datetime(df['report_date_as_yyyy_mm_dd'])
    
    # TFF uses different categories, we'll map them to the same structure for easy comparison where applicable
    # or keep them distinct. For the dashboard, we'll map:
    # Dealers -> Commercials
    # Leveraged Money -> Large Specs
    # Non-Reportable -> Small Specs
    
    normalized_df = pd.DataFrame({
        'Date': df['report_date_as_yyyy_mm_dd'],
        'Contract_Code': df['cftc_contract_market_code'],
        'Report_Type': 'tff',
        'Open_Interest': df['open_interest_all'],
        
        # Dealers (Analogous to Commercials)
        'Comm_Long': df['dealer_positions_long_all'],
        'Comm_Short': df['dealer_positions_short_all'],
        'Comm_Net': df['dealer_positions_long_all'] - df['dealer_positions_short_all'],
        
        # Leveraged Funds (Analogous to Large Specs)
        'Large_Spec_Long': df['lev_money_positions_long'],
        'Large_Spec_Short': df['lev_money_positions_short'],
        'Large_Spec_Net': df['lev_money_positions_long'] - df['lev_money_positions_short'],
        
        # Small Specs (Non-Reportable)
        'Small_Spec_Long': df['nonrept_positions_long_all'],
        'Small_Spec_Short': df['nonrept_positions_short_all'],
        'Small_Spec_Net': df['nonrept_positions_long_all'] - df['nonrept_positions_short_all'],
        
        # Keep extra TFF specific fields
        'Asset_Mgr_Net': df['asset_mgr_positions_long'] - df['asset_mgr_positions_short'],
        'Other_Rept_Net': df['other_rept_positions_long'] - df['other_rept_positions_short']
    })
    
    return normalized_df
