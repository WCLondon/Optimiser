"""
BNG Metric Reader Module
Extracts requirements from DEFRA BNG metric Excel files
"""

import io
import os
import re
from typing import Dict, List, Optional, Tuple

import pandas as pd


# ------------- open workbook -------------
def open_metric_workbook(uploaded_file) -> pd.ExcelFile:
    """Open a BNG metric workbook (.xlsx, .xlsm, .xlsb)"""
    data = uploaded_file.read() if hasattr(uploaded_file, "read") else uploaded_file
    name = getattr(uploaded_file, "name", "") or ""
    ext = os.path.splitext(name)[1].lower()
    if ext in [".xlsx", ".xlsm", ""]:
        try: 
            return pd.ExcelFile(io.BytesIO(data), engine="openpyxl")
        except Exception: 
            pass
    if ext == ".xlsb":
        try: 
            return pd.ExcelFile(io.BytesIO(data), engine="pyxlsb")
        except Exception: 
            pass
    for eng in ("openpyxl", "pyxlsb"):
        try: 
            return pd.ExcelFile(io.BytesIO(data), engine=eng)
        except Exception: 
            continue
    raise RuntimeError("Could not open workbook. Try re-saving as .xlsx or .xlsm.")


# ------------- utils -------------
def clean_text(x) -> str:
    """Clean and normalize text"""
    if x is None or (isinstance(x, float) and pd.isna(x)): 
        return ""
    return re.sub(r"\s+", " ", str(x).strip())


def canon(s: str) -> str:
    """Canonicalize string for comparison"""
    s = clean_text(s).lower().replace("–","-").replace("—","-")
    return re.sub(r"[^a-z0-9]+","_", s).strip("_")


def coerce_num(s: pd.Series) -> pd.Series:
    """Convert series to numeric, coercing errors to NaN"""
    return pd.to_numeric(s, errors="coerce")


def find_sheet(xls: pd.ExcelFile, targets: List[str]) -> Optional[str]:
    """Find a sheet by matching against target names"""
    existing = {canon(s): s for s in xls.sheet_names}
    for t in targets:
        if canon(t) in existing: 
            return existing[canon(t)]
    for s in xls.sheet_names:
        if any(canon(t) in canon(s) for t in targets): 
            return s
    return None


def find_header_row(df: pd.DataFrame, within_rows: int = 80) -> Optional[int]:
    """Find the header row in a trading summary sheet"""
    for i in range(min(within_rows, len(df))):
        row = " ".join([clean_text(x) for x in df.iloc[i].tolist()]).lower()
        if ("group" in row) and (("on-site" in row and "off-site" in row and "project" in row)
                                 or "project wide" in row or "project-wide" in row):
            return i
    return None


def col_like(df: pd.DataFrame, *cands: str) -> Optional[str]:
    """Find a column that matches any of the candidate names"""
    cols = {canon(c): c for c in df.columns}
    for c in cands:
        if canon(c) in cols: 
            return cols[canon(c)]
    for k, v in cols.items():
        if any(canon(c) in k for c in cands): 
            return v
    return None


# ------------- loaders -------------
def load_raw_sheet(xls: pd.ExcelFile, sheet: str) -> pd.DataFrame:
    """Load a sheet without parsing headers"""
    return pd.read_excel(xls, sheet_name=sheet, header=None)


def load_trading_df(xls: pd.ExcelFile, sheet: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load and parse a trading summary sheet"""
    raw = load_raw_sheet(xls, sheet)
    hdr = find_header_row(raw)
    if hdr is None:
        df = pd.read_excel(xls, sheet_name=sheet)  # fallback
    else:
        headers = raw.iloc[hdr].map(clean_text).tolist()
        df = raw.iloc[hdr + 1:].copy()
        df.columns = headers
    df = df.loc[:, ~df.columns.duplicated()].copy()
    df = df.dropna(how="all").reset_index(drop=True)
    return df, raw


# ------------- broad group from right -------------
def resolve_broad_group_col(df: pd.DataFrame, habitat_col: str, broad_col_guess: Optional[str]) -> Optional[str]:
    """Determine the broad group column (usually to the right of habitat column)"""
    try:
        h_idx = df.columns.get_loc(habitat_col)
        adj = df.columns[h_idx + 1] if h_idx + 1 < len(df.columns) else None
    except Exception:
        adj = None
    
    def looks_like_group(col: Optional[str]) -> bool:
        if not col or col not in df.columns: 
            return False
        name = canon(col)
        if any(k in name for k in ["group","broad_habitat"]): 
            return True
        ser = df[col].dropna()
        if ser.empty: 
            return False
        return pd.to_numeric(ser, errors="coerce").notna().mean() < 0.2
    
    if adj and looks_like_group(adj) and "unit_change" not in canon(adj): 
        return adj
    if broad_col_guess and looks_like_group(broad_col_guess): 
        return broad_col_guess
    if adj and "unit_change" not in canon(adj): 
        return adj
    return broad_col_guess


# ------------- distinctiveness from raw headers -------------
VH_PAT = re.compile(r"\bvery\s*high\b.*distinct", re.I)
H_PAT  = re.compile(r"\bhigh\b.*distinct", re.I)
M_PAT  = re.compile(r"\bmedium\b.*distinct", re.I)
L_PAT  = re.compile(r"\blow\b.*distinct", re.I)


def build_band_map_from_raw(raw: pd.DataFrame, habitats: List[str]) -> Dict[str, str]:
    """Extract distinctiveness bands from raw sheet headers"""
    target_set = {clean_text(h) for h in habitats if isinstance(h, str) and clean_text(h)}
    band_map: Dict[str, str] = {}
    active_band: Optional[str] = None
    max_scan_cols = min(8, raw.shape[1])
    
    for r in range(len(raw)):
        texts = []
        for c in range(max_scan_cols):
            val = raw.iat[r, c] if c < raw.shape[1] else None
            if isinstance(val, str) or (isinstance(val, float) and not pd.isna(val)):
                texts.append(clean_text(val))
        joined = " ".join([t for t in texts if t]).strip()
        
        if joined:
            if VH_PAT.search(joined): 
                active_band = "Very High"
            elif H_PAT.search(joined) and not VH_PAT.search(joined): 
                active_band = "High"
            elif M_PAT.search(joined): 
                active_band = "Medium"
            elif L_PAT.search(joined): 
                active_band = "Low"
        
        if active_band:
            for c in range(raw.shape[1]):
                val = raw.iat[r, c]
                if isinstance(val, str):
                    v = clean_text(val)
                    if v in target_set and v not in band_map:
                        band_map[v] = active_band
    
    return band_map


# ------------- normalise (generic) -------------
def normalise_requirements(
    xls: pd.ExcelFile,
    sheet_candidates: List[str],
    category_label: str
) -> Tuple[pd.DataFrame, Dict[str, str], str]:
    """
    Parse a trading summary sheet and extract requirements.
    Returns: (normalized_df, column_map, sheet_name)
    """
    sheet = find_sheet(xls, sheet_candidates) or ""
    if not sheet:
        return pd.DataFrame(columns=[
            "category","habitat","broad_group","distinctiveness","project_wide_change","on_site_change"
        ]), {}, sheet
    
    df, raw = load_trading_df(xls, sheet)
    habitat_col = col_like(df, "Habitat", "Feature")
    broad_col_guess = col_like(df, "Habitat group", "Broad habitat", "Group")
    proj_col = col_like(df, "Project-wide unit change", "Project wide unit change")
    ons_col  = col_like(df, "On-site unit change", "On site unit change")
    
    if not habitat_col or not proj_col:
        return pd.DataFrame(columns=[
            "category","habitat","broad_group","distinctiveness","project_wide_change","on_site_change"
        ]), {}, sheet
    
    broad_col = resolve_broad_group_col(df, habitat_col, broad_col_guess)
    df = df[~df[habitat_col].isna()]
    df = df[df[habitat_col].astype(str).str.strip() != ""].copy()
    
    for c in [proj_col, ons_col]:
        if c in df.columns: 
            df[c] = coerce_num(df[c])
    
    habitat_list = df[habitat_col].astype(str).map(clean_text).tolist()
    band_map = build_band_map_from_raw(raw, habitat_list)
    df["__distinctiveness__"] = df[habitat_col].astype(str).map(lambda x: band_map.get(clean_text(x), pd.NA))
    
    out = pd.DataFrame({
        "category": category_label,
        "habitat": df[habitat_col],
        "broad_group": df[broad_col] if (broad_col in df.columns) else pd.NA,
        "distinctiveness": df["__distinctiveness__"],
        "project_wide_change": df[proj_col],
        "on_site_change": df[ons_col] if ons_col in df.columns else pd.NA,
    })
    
    colmap = {
        "habitat": habitat_col, 
        "broad_group": broad_col or "",
        "project_wide_change": proj_col, 
        "on_site_change": ons_col or "",
        "distinctiveness_from_raw": "__distinctiveness__",
    }
    
    return out.reset_index(drop=True), colmap, sheet


def parse_metric_requirements(uploaded_file) -> Dict[str, pd.DataFrame]:
    """
    Main entry point: parse a BNG metric file and return requirements.
    Returns dict with keys: 'area', 'hedgerows', 'watercourses'
    Each value is a DataFrame with columns: habitat, units (negative values only = deficits)
    """
    try:
        xls = open_metric_workbook(uploaded_file)
    except Exception as e:
        raise RuntimeError(f"Could not open workbook: {e}")
    
    # Sheet name candidates
    AREA_SHEETS = [
        "Trading Summary Area Habitats",
        "Area Habitats Trading Summary",
        "Area Trading Summary",
        "Trading Summary (Area Habitats)"
    ]
    HEDGE_SHEETS = [
        "Trading Summary Hedgerows",
        "Hedgerows Trading Summary",
        "Hedgerow Trading Summary",
        "Trading Summary (Hedgerows)"
    ]
    WATER_SHEETS = [
        "Trading Summary WaterCs",
        "Trading Summary Watercourses",
        "Watercourses Trading Summary",
        "Trading Summary (Watercourses)"
    ]
    
    # Parse each category
    area_norm, _, _ = normalise_requirements(xls, AREA_SHEETS, "Area Habitats")
    hedge_norm, _, _ = normalise_requirements(xls, HEDGE_SHEETS, "Hedgerows")
    water_norm, _, _ = normalise_requirements(xls, WATER_SHEETS, "Watercourses")
    
    # Extract deficits (negative project_wide_change values)
    def extract_deficits(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=["habitat", "units"])
        
        df = df.copy()
        df["project_wide_change"] = coerce_num(df["project_wide_change"])
        deficits = df[df["project_wide_change"] < 0].copy()
        
        if deficits.empty:
            return pd.DataFrame(columns=["habitat", "units"])
        
        # Convert to positive units (absolute value)
        result = pd.DataFrame({
            "habitat": deficits["habitat"].astype(str).map(clean_text),
            "units": deficits["project_wide_change"].abs()
        })
        
        return result.reset_index(drop=True)
    
    return {
        "area": extract_deficits(area_norm),
        "hedgerows": extract_deficits(hedge_norm),
        "watercourses": extract_deficits(water_norm)
    }
