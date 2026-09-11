import os

# Socrata API Endpoints (Futures Only)
LEGACY_DATASET_ID = "6dca-aqww"
TFF_DATASET_ID = "gpe5-46if"
API_BASE_URL = "https://publicreporting.cftc.gov/resource/"

# Local Storage
DB_PATH = os.path.join(os.path.dirname(__file__), "cot_data.db")

# Instrument Configuration
# Mapping Display Name -> { "code": CFTC Contract Market Code, "report_type": "legacy" | "tff", "group": Asset Class, "cot_available": True/False }
INSTRUMENT_CONFIG = {
    # EQUITIES (TFF)
    "E-Mini S&P 500": {"code": "13874A", "report_type": "tff", "group": "Equities", "cot_available": True},
    "E-Mini Nasdaq 100": {"code": "209742", "report_type": "tff", "group": "Equities", "cot_available": True},
    "E-Mini Dow": {"code": "124603", "report_type": "tff", "group": "Equities", "cot_available": True},
    "E-Mini Russell 2000": {"code": "239742", "report_type": "tff", "group": "Equities", "cot_available": True},
    "VIX": {"code": "1170E1", "report_type": "tff", "group": "Equities", "cot_available": True},
    
    # FOREX (TFF)
    "Euro FX": {"code": "099741", "report_type": "tff", "group": "Forex", "cot_available": True},
    "Japanese Yen": {"code": "097741", "report_type": "tff", "group": "Forex", "cot_available": True},
    "British Pound": {"code": "096742", "report_type": "tff", "group": "Forex", "cot_available": True},
    "Australian Dollar": {"code": "232741", "report_type": "tff", "group": "Forex", "cot_available": True},
    "Canadian Dollar": {"code": "090741", "report_type": "tff", "group": "Forex", "cot_available": True},
    "Swiss Franc": {"code": "092741", "report_type": "tff", "group": "Forex", "cot_available": True},
    "New Zealand Dollar": {"code": "112741", "report_type": "tff", "group": "Forex", "cot_available": True},
    "Mexican Peso": {"code": "095741", "report_type": "tff", "group": "Forex", "cot_available": True},
    "USD Index": {"code": "098662", "report_type": "tff", "group": "Forex", "cot_available": True},
    
    # RATES (TFF)
    "US Treasury Bond (30Y)": {"code": "020601", "report_type": "tff", "group": "Rates", "cot_available": True},
    "US 10Y Note": {"code": "043602", "report_type": "tff", "group": "Rates", "cot_available": True},
    "US 5Y Note": {"code": "044601", "report_type": "tff", "group": "Rates", "cot_available": True},
    "US 2Y Note": {"code": "042601", "report_type": "tff", "group": "Rates", "cot_available": True},
    "SOFR 3M": {"code": "134741", "report_type": "tff", "group": "Rates", "cot_available": True},
    
    # CRYPTO (TFF)
    "Bitcoin": {"code": "133741", "report_type": "tff", "group": "Crypto", "cot_available": True},
    "Ether": {"code": "146021", "report_type": "tff", "group": "Crypto", "cot_available": True},
    
    # METALS (Legacy)
    "Gold": {"code": "088691", "report_type": "legacy", "group": "Metals", "cot_available": True},
    "Silver": {"code": "084691", "report_type": "legacy", "group": "Metals", "cot_available": True},
    "Copper": {"code": "085691", "report_type": "legacy", "group": "Metals", "cot_available": True},
    "Platinum": {"code": "076651", "report_type": "legacy", "group": "Metals", "cot_available": True},
    "Palladium": {"code": "075651", "report_type": "legacy", "group": "Metals", "cot_available": True},
    "LME Aluminum": {"code": "N/A", "report_type": "legacy", "group": "Metals", "cot_available": False}, # Example non-reportable
    
    # ENERGY (Legacy)
    "WTI Crude Oil": {"code": "06765I", "report_type": "legacy", "group": "Energy", "cot_available": True}, # WTI Financial / Light Sweet
    "Brent Crude Oil": {"code": "06765T", "report_type": "legacy", "group": "Energy", "cot_available": True}, # Brent Last Day
    "Natural Gas": {"code": "023651", "report_type": "legacy", "group": "Energy", "cot_available": True},
    "RBOB Gasoline": {"code": "111659", "report_type": "legacy", "group": "Energy", "cot_available": True},
    "NY Harbor ULSD (Heating Oil)": {"code": "022651", "report_type": "legacy", "group": "Energy", "cot_available": True},
    
    # AGRICULTURE (Legacy)
    "Corn": {"code": "002602", "report_type": "legacy", "group": "Agriculture", "cot_available": True},
    "Soybeans": {"code": "005602", "report_type": "legacy", "group": "Agriculture", "cot_available": True},
    "Wheat (SRW)": {"code": "001602", "report_type": "legacy", "group": "Agriculture", "cot_available": True},
    "Sugar #11": {"code": "080732", "report_type": "legacy", "group": "Agriculture", "cot_available": True},
    "Coffee C": {"code": "083731", "report_type": "legacy", "group": "Agriculture", "cot_available": True},
    "Cocoa": {"code": "073732", "report_type": "legacy", "group": "Agriculture", "cot_available": True},
    "Cotton #2": {"code": "033661", "report_type": "legacy", "group": "Agriculture", "cot_available": True},
    "Live Cattle": {"code": "057642", "report_type": "legacy", "group": "Agriculture", "cot_available": True},
}

# Useful groupings
GROUPS = sorted(list(set(v["group"] for v in INSTRUMENT_CONFIG.values())))
