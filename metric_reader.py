"""
BNG Metric Reader Module
Extracts requirements from DEFRA BNG metric Excel files

Watercourse Spatial Risk Multiplier (SRM) Requirements:
-------------------------------------------------------
For watercourse habitats, SRM is determined by catchment proximity:
- Same waterbody catchment → SRM = 1.0 (no uplift)
- Same operational catchment (different waterbody) → SRM = 0.75 (effective 4/3 uplift to buyer requirement)
- Outside operational catchment → SRM = 0.5 (effective 2× uplift to buyer requirement)

SRM multipliers work TOGETHER with trading rules:
- Passing trading rules doesn't remove SRM requirements
- Meeting SRM proximity doesn't relax trading rules
- Both must be satisfied for valid offsetting

Waterbody and operational catchment data should be obtained from:
- Environment Agency Water Framework Directive (WFD) datasets
- Available via https://environment.data.gov.uk/
"""

import io
import os
import re
import warnings
from typing import Dict, List, Optional, Tuple

import pandas as pd


# ------------- Medium distinctiveness hierarchy -------------
# Priority Medium broad groups (processed before secondary groups during on-site offsets)
PRIORITY_MEDIUM_GROUPS = {
    "cropland",
    "lakes",
    "sparsely vegetated land",
    "urban",
    "individual trees",
    "woodland and forest",
    "intertidal sediment",
    "intertidal hard structures"
}

# Secondary Medium broad groups: Grassland, Heathland and shrub
# (processed after priority groups)


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
        # Check for area habitat headers (with group column)
        if ("group" in row) and (("on-site" in row and "off-site" in row and "project" in row)
                                 or "project wide" in row or "project-wide" in row):
            return i
        # Check for hedgerow/watercourse headers (without group column)
        # Look for "habitat" or "feature" combined with "project-wide unit change" or similar
        if (("habitat" in row or "feature" in row) and 
            ("project" in row and ("unit" in row or "change" in row))):
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


def col_exact(df: pd.DataFrame, *cands: str) -> Optional[str]:
    """Find a column that exactly matches any of the candidate names (after canonicalization).
    
    Unlike col_like(), this does NOT do substring matching. This is important for columns
    like 'Distinctiveness' where we don't want to match summary columns like
    'Medium Distinctiveness net change in units'.
    """
    cols = {canon(c): c for c in df.columns}
    for c in cands:
        if canon(c) in cols:
            return cols[canon(c)]
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
        # Exclude distinctiveness columns
        if any(k in name for k in ["distinct"]):
            return False
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
    # Don't return adj if it doesn't look like a group (e.g., could be a Distinctiveness column)
    return broad_col_guess


# ------------- distinctiveness from raw headers -------------
VH_PAT = re.compile(r"\bvery\s*high\b.*distinct", re.I)
H_PAT  = re.compile(r"\bhigh\b.*distinct", re.I)
M_PAT  = re.compile(r"\bmedium\b.*distinct", re.I)
VL_PAT = re.compile(r"\bvery\s*low\b.*distinct", re.I)
L_PAT  = re.compile(r"\blow\b.*distinct", re.I)


def build_band_map_from_raw(raw: pd.DataFrame, habitats: List[str], debug=False) -> Dict[str, str]:
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
                if debug: print(f"  Row {r}: Found 'Very High' in: {joined[:80]}")
            elif H_PAT.search(joined) and not VH_PAT.search(joined): 
                active_band = "High"
                if debug: print(f"  Row {r}: Found 'High' in: {joined[:80]}")
            elif M_PAT.search(joined): 
                active_band = "Medium"
                if debug: print(f"  Row {r}: Found 'Medium' in: {joined[:80]}")
            elif VL_PAT.search(joined):
                active_band = "Very Low"
                if debug: print(f"  Row {r}: Found 'Very Low' in: {joined[:80]}")
            elif L_PAT.search(joined): 
                active_band = "Low"
                if debug: print(f"  Row {r}: Found 'Low' in: {joined[:80]}")
        
        if active_band:
            for c in range(raw.shape[1]):
                val = raw.iat[r, c]
                if isinstance(val, str):
                    v = clean_text(val)
                    if v in target_set and v not in band_map:
                        band_map[v] = active_band
                        if debug: print(f"    -> Mapped habitat '{v}' to '{active_band}'")
    
    if debug:
        print(f"\n  Total habitats in target_set: {len(target_set)}")
        print(f"  Total mapped: {len(band_map)}")
        if len(band_map) < len(target_set):
            unmapped = target_set - set(band_map.keys())
            print(f"  ⚠️  Unmapped habitats ({len(unmapped)}): {list(unmapped)[:5]}")
    
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
    
    # Filter out rows where project_wide_change is NaN (section headers, repeated headers)
    df = df[~df[proj_col].isna()].copy()
    
    # Check if there's a Distinctiveness column in the dataframe
    # Use col_exact() to avoid matching summary columns like "Medium Distinctiveness net change in units"
    distinctiveness_col = col_exact(df, "Distinctiveness", "Distinct")
    
    if distinctiveness_col and distinctiveness_col in df.columns:
        # Use the Distinctiveness column directly
        df["__distinctiveness__"] = df[distinctiveness_col].astype(str).map(clean_text)
    else:
        # Fall back to extracting from section headers
        habitat_list = df[habitat_col].astype(str).map(clean_text).tolist()
        band_map = build_band_map_from_raw(raw, habitat_list, debug=False)
        df["__distinctiveness__"] = df[habitat_col].astype(str).map(lambda x: band_map.get(clean_text(x), pd.NA))
        
        # Validate: check if distinctiveness extraction succeeded for deficits
        # Only deficits need distinctiveness for trading rules to work
        has_deficits = (pd.to_numeric(df[proj_col], errors="coerce") < 0).any()
        if has_deficits:
            deficit_rows = df[pd.to_numeric(df[proj_col], errors="coerce") < 0]
            na_count = deficit_rows["__distinctiveness__"].isna().sum()
            if na_count > 0:
                # WARNING: Some deficits have NA distinctiveness, which will prevent proper offsetting
                warnings.warn(
                    f"{category_label}: {na_count} deficit habitat(s) have undefined distinctiveness. "
                    f"Trading rules may not apply correctly. Check metric file format.",
                    UserWarning
                )
    
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


# ------------- distinctiveness validation -------------
def is_invalid_distinctiveness(band) -> bool:
    """Check if a distinctiveness band value is invalid/unknown"""
    if pd.isna(band):
        return True
    band_str = str(band).lower().strip()
    return band_str in ['nan', 'none', '', '<na>']


# ------------- area trading rules -------------
def can_offset_area(d_band: str, d_broad: str, d_hab: str,
                    s_band: str, s_broad: str, s_hab: str) -> bool:
    """
    Check if surplus can offset deficit according to area habitat trading rules.
    
    Trading rules for area habitats:
    - Very High: Same habitat required (like-for-like)
    - High: Same habitat required (like-for-like)
    - Medium: High/Very High can offset from any broad group; Medium can offset Medium only if same broad group
    - Low: Same distinctiveness or better
    
    If distinctiveness is NA/unknown, returns False to prevent incorrect offsetting.
    """
    # Handle NA or invalid distinctiveness - prevent offsetting if we don't know the bands
    if is_invalid_distinctiveness(d_band) or is_invalid_distinctiveness(s_band):
        return False
    
    rank = {"Low":1, "Medium":2, "High":3, "Very High":4}
    rd = rank.get(str(d_band), -1)  # -1 if not found
    rs = rank.get(str(s_band), -1)
    
    # If either rank is unknown, don't allow offsetting
    if rd < 0 or rs < 0:
        return False
    
    d_broad = clean_text(d_broad)
    s_broad = clean_text(s_broad)
    d_hab = clean_text(d_hab)
    s_hab = clean_text(s_hab)
    
    if d_band == "Very High": 
        return d_hab == s_hab
    if d_band == "High":      
        return d_hab == s_hab
    if d_band == "Medium":
        # High or Very High can offset Medium from any broad group
        if rs > rd:  # High (3) or Very High (4) > Medium (2)
            return True
        # Medium can offset Medium only if same broad group
        if rs == rd:  # Both Medium
            return d_broad != "" and d_broad == s_broad
        return False
    if d_band == "Low":       
        return rs >= rd
    return False


def can_offset_hedgerow(d_band: str, d_hab: str, s_band: str, s_hab: str) -> bool:
    """
    Check if hedgerow surplus can offset hedgerow deficit according to hedgerow trading rules.
    
    Trading rules for hedgerows:
    - Very High: Same habitat required (like-for-like)
    - High: Like for like or better (same habitat required)
    - Medium: Same distinctiveness or better
    - Low: Same distinctiveness or better
    - Very Low: Same distinctiveness or better
    
    If distinctiveness is NA/unknown, returns False to prevent incorrect offsetting.
    """
    # Handle NA or invalid distinctiveness - prevent offsetting if we don't know the bands
    if is_invalid_distinctiveness(d_band) or is_invalid_distinctiveness(s_band):
        return False
    
    rank = {"Very Low": 0, "Low": 1, "Medium": 2, "High": 3, "Very High": 4}
    rd = rank.get(str(d_band), -1)  # -1 if not found
    rs = rank.get(str(s_band), -1)
    
    # If either rank is unknown, don't allow offsetting
    if rd < 0 or rs < 0:
        return False
    
    d_hab = clean_text(d_hab)
    s_hab = clean_text(s_hab)
    
    if d_band == "Very High":
        return d_hab == s_hab  # Same habitat required
    if d_band == "High":
        return d_hab == s_hab  # Like for like or better (same habitat)
    # For Medium, Low, Very Low: same distinctiveness or better
    return rs >= rd


def can_offset_watercourse(d_band: str, d_hab: str, s_band: str, s_hab: str) -> bool:
    """
    Check if watercourse surplus can offset watercourse deficit according to watercourse trading rules.
    
    Trading rules for watercourses:
    - Very High: Not eligible for normal trading (bespoke compensation required) - return False
    - High: Same habitat required (like-for-like, no trading up or down)
    - Medium: Same habitat required (like-for-like, no trading up or down)
    - Low: Must trade to better distinctiveness habitat (cannot offset Low with Low)
    
    "Same habitat" means the same watercourse habitat type (e.g., rivers/streams with rivers/streams,
    canals with canals, ditches with ditches) with equal distinctiveness where required.
    
    If distinctiveness is NA/unknown, returns False to prevent incorrect offsetting.
    """
    # Handle NA or invalid distinctiveness - prevent offsetting if we don't know the bands
    if is_invalid_distinctiveness(d_band) or is_invalid_distinctiveness(s_band):
        return False
    
    rank = {"Low": 1, "Medium": 2, "High": 3, "Very High": 4}
    rd = rank.get(str(d_band), -1)  # -1 if not found
    rs = rank.get(str(s_band), -1)
    
    # If either rank is unknown, don't allow offsetting
    if rd < 0 or rs < 0:
        return False
    
    d_hab = clean_text(d_hab)
    s_hab = clean_text(s_hab)
    
    # Normalize habitat names to canonical forms for watercourse matching
    # This helps match "Other rivers and streams" with "rivers and streams", etc.
    def normalize_watercourse_habitat(hab: str) -> str:
        hab_lower = hab.lower()
        # Map common variations to canonical forms
        if "river" in hab_lower or "stream" in hab_lower:
            return "rivers_streams"
        elif "canal" in hab_lower:
            return "canals"
        elif "ditch" in hab_lower:
            return "ditches"
        elif "culvert" in hab_lower:
            return "culvert"
        elif "priority habitat" in hab_lower:
            return "priority_habitat"
        return hab_lower.replace(" ", "_")
    
    d_hab_norm = normalize_watercourse_habitat(d_hab)
    s_hab_norm = normalize_watercourse_habitat(s_hab)
    
    if d_band == "Very High":
        # Very High watercourses require bespoke compensation - not eligible for normal trading
        return False
    
    if d_band == "High":
        # High: same habitat required (like-for-like), same or better distinctiveness
        return d_hab_norm == s_hab_norm and rs >= rd
    
    if d_band == "Medium":
        # Medium: same habitat required (like-for-like), same or better distinctiveness
        return d_hab_norm == s_hab_norm and rs >= rd
    
    if d_band == "Low":
        # Low: must trade to better distinctiveness habitat (cannot offset Low with Low)
        # Surplus must be higher distinctiveness AND same habitat type
        return rs > rd and d_hab_norm == s_hab_norm
    
    return False


def apply_area_offsets(area_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Apply on-site trading rules and calculate residual deficits.
    Returns dict with:
      - residual_off_site: unmet deficits after on-site offsets
      - surplus_after_offsets_detail: remaining surpluses
      - flow_log: list of allocation records with priority_medium flag
    """
    data = area_df.copy()
    data["project_wide_change"] = coerce_num(data["project_wide_change"])
    deficits = data[data["project_wide_change"] < 0].copy()
    surpluses = data[data["project_wide_change"] > 0].copy()

    # Working copy to track remaining surplus
    sur = surpluses.copy()
    sur["__remain__"] = sur["project_wide_change"].astype(float)

    band_rank = {"Low": 1, "Medium": 2, "High": 3, "Very High": 4}
    
    # Sub-ranking boost for priority Medium groups to ensure they're processed
    # between regular Medium (2.0) and High (3.0) distinctiveness
    MEDIUM_PRIORITY_BOOST = 0.5
    
    # Sort deficits by:
    # 1. Distinctiveness rank (Very High > High > Medium > Low)
    # 2. For Medium: priority group first, then secondary group
    # 3. Original order within each group
    def deficit_sort_key(row_tuple):
        idx, row = row_tuple
        d_band = str(row["distinctiveness"])
        d_broad = clean_text(row.get("broad_group", "")).lower()
        
        rank = band_rank.get(d_band, 0)
        
        # For Medium distinctiveness, add sub-ranking
        if d_band == "Medium":
            is_priority = d_broad in PRIORITY_MEDIUM_GROUPS
            # Priority group gets rank 2.5 (between Medium 2 and High 3)
            # Secondary group keeps rank 2.0
            sub_rank = MEDIUM_PRIORITY_BOOST if is_priority else 0.0
            return (-rank - sub_rank, idx)
        
        return (-rank, idx)
    
    sorted_deficits = sorted(deficits.iterrows(), key=deficit_sort_key)
    
    # Track what each deficit received
    deficit_received = {}
    
    # Flow log to track allocations
    flow_log = []
    
    # Apply trading rules to offset deficits with surpluses
    for di, d in sorted_deficits:
        need = abs(float(d["project_wide_change"]))
        d_band  = str(d["distinctiveness"])
        d_broad = clean_text(d.get("broad_group",""))
        d_hab   = clean_text(d.get("habitat",""))
        
        # Check if this is a priority Medium group
        is_priority_medium = (d_band == "Medium" and 
                             d_broad.lower() in PRIORITY_MEDIUM_GROUPS)
        
        deficit_key = (di, d_hab, d_broad, d_band)
        deficit_received[deficit_key] = 0.0
        
        # Find eligible surpluses
        elig_idx = [si for si, s in sur.iterrows()
                    if can_offset_area(d_band, d_broad, d_hab,
                                       str(s["distinctiveness"]), 
                                       clean_text(s.get("broad_group","")),
                                       clean_text(s.get("habitat","")))
                    and sur.loc[si,"__remain__"] > 0]
        
        # Sort by priority: higher distinctiveness first, then larger surplus
        elig_idx = sorted(elig_idx,
                          key=lambda i: (-band_rank.get(str(sur.loc[i,"distinctiveness"]),0),
                                         -sur.loc[i,"__remain__"]))
        
        # Allocate surpluses to deficit
        for i in elig_idx:
            if need <= 1e-9: 
                break
            give = min(need, float(sur.loc[i,"__remain__"]))
            if give <= 0: 
                continue
            sur.loc[i,"__remain__"] -= give
            deficit_received[deficit_key] += give
            need -= give
            
            # Log this allocation
            flow_log.append({
                "deficit_habitat": d_hab,
                "deficit_broad_group": d_broad,
                "deficit_distinctiveness": d_band,
                "surplus_habitat": clean_text(sur.loc[i, "habitat"]),
                "surplus_broad_group": clean_text(sur.loc[i, "broad_group"]),
                "surplus_distinctiveness": str(sur.loc[i, "distinctiveness"]),
                "units_allocated": round(give, 6),
                "priority_medium": is_priority_medium
            })

    # Calculate residual unmet deficits
    remaining_records = []
    
    for di, d in deficits.iterrows():
        d_hab   = clean_text(d.get("habitat",""))
        d_broad = clean_text(d.get("broad_group",""))
        d_band  = str(d["distinctiveness"])
        
        original_need = abs(float(d["project_wide_change"]))
        deficit_key = (di, d_hab, d_broad, d_band)
        received = deficit_received.get(deficit_key, 0.0)
        unmet = max(original_need - received, 0.0)
        
        if unmet > 1e-4:  # Filter out floating-point errors
            remaining_records.append({
                "habitat": d_hab,
                "broad_group": d_broad,
                "distinctiveness": d_band,
                "unmet_units_after_on_site_offset": round(unmet, 6)
            })

    # Detail table of remaining surpluses (for headline allocation)
    surplus_after_offsets_detail = sur.rename(columns={"__remain__":"surplus_remaining_units"})[
        ["habitat","broad_group","distinctiveness","surplus_remaining_units"]
    ].copy()

    return {
        "residual_off_site": pd.DataFrame(remaining_records).reset_index(drop=True) if remaining_records else pd.DataFrame(columns=["habitat","broad_group","distinctiveness","unmet_units_after_on_site_offset"]),
        "surplus_after_offsets_detail": surplus_after_offsets_detail,
        "flow_log": flow_log
    }


def apply_hedgerow_offsets(hedge_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Apply on-site trading rules for hedgerows and calculate residual deficits.
    Returns dict with:
      - residual_off_site: unmet deficits after on-site offsets
      - surplus_after_offsets_detail: remaining surpluses
    
    Hedgerow trading rules (simpler than area habitats):
    - Very High & High: Same habitat required (like-for-like)
    - Medium, Low, Very Low: Same distinctiveness or better
    """
    data = hedge_df.copy()
    data["project_wide_change"] = coerce_num(data["project_wide_change"])
    deficits = data[data["project_wide_change"] < 0].copy()
    surpluses = data[data["project_wide_change"] > 0].copy()

    # Working copy to track remaining surplus
    sur = surpluses.copy()
    sur["__remain__"] = sur["project_wide_change"].astype(float)

    band_rank = {"Very Low": 0, "Low": 1, "Medium": 2, "High": 3, "Very High": 4}
    
    # Sort deficits by distinctiveness rank (Very High > High > Medium > Low > Very Low)
    sorted_deficits = sorted(deficits.iterrows(), 
                            key=lambda t: (-band_rank.get(str(t[1]["distinctiveness"]), 0), t[0]))
    
    # Track what each deficit received
    deficit_received = {}
    
    # Apply trading rules to offset deficits with surpluses
    for di, d in sorted_deficits:
        need = abs(float(d["project_wide_change"]))
        d_band = str(d["distinctiveness"])
        d_hab = clean_text(d.get("habitat", ""))
        
        deficit_key = (di, d_hab, d_band)
        deficit_received[deficit_key] = 0.0
        
        # Find eligible surpluses
        elig_idx = [si for si, s in sur.iterrows()
                    if can_offset_hedgerow(d_band, d_hab,
                                          str(s["distinctiveness"]),
                                          clean_text(s.get("habitat", "")))
                    and sur.loc[si, "__remain__"] > 0]
        
        # Sort by priority: higher distinctiveness first, then larger surplus
        elig_idx = sorted(elig_idx,
                         key=lambda i: (-band_rank.get(str(sur.loc[i, "distinctiveness"]), 0),
                                       -sur.loc[i, "__remain__"]))
        
        # Allocate surpluses to deficit
        for i in elig_idx:
            if need <= 1e-9:
                break
            give = min(need, float(sur.loc[i, "__remain__"]))
            if give <= 0:
                continue
            sur.loc[i, "__remain__"] -= give
            deficit_received[deficit_key] += give
            need -= give

    # Calculate residual unmet deficits
    remaining_records = []
    
    for di, d in deficits.iterrows():
        d_hab = clean_text(d.get("habitat", ""))
        d_band = str(d["distinctiveness"])
        
        original_need = abs(float(d["project_wide_change"]))
        deficit_key = (di, d_hab, d_band)
        received = deficit_received.get(deficit_key, 0.0)
        unmet = max(original_need - received, 0.0)
        
        if unmet > 1e-4:  # Filter out floating-point errors
            remaining_records.append({
                "habitat": d_hab,
                "distinctiveness": d_band,
                "unmet_units_after_on_site_offset": round(unmet, 6)
            })

    # Detail table of remaining surpluses (for headline allocation)
    surplus_after_offsets_detail = sur.rename(columns={"__remain__": "surplus_remaining_units"})[
        ["habitat", "distinctiveness", "surplus_remaining_units"]
    ].copy()

    return {
        "residual_off_site": pd.DataFrame(remaining_records).reset_index(drop=True) if remaining_records else pd.DataFrame(columns=["habitat", "distinctiveness", "unmet_units_after_on_site_offset"]),
        "surplus_after_offsets_detail": surplus_after_offsets_detail
    }


def apply_watercourse_offsets(water_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Apply on-site trading rules for watercourses and calculate residual deficits.
    Returns dict with:
      - residual_off_site: unmet deficits after on-site offsets
      - surplus_after_offsets_detail: remaining surpluses
    
    Watercourse trading rules:
    - Very High: Not eligible for normal trading (bespoke compensation required)
    - High: Same habitat required (like-for-like)
    - Medium: Same habitat required (like-for-like)
    - Low: Must trade to better distinctiveness habitat
    """
    data = water_df.copy()
    data["project_wide_change"] = coerce_num(data["project_wide_change"])
    deficits = data[data["project_wide_change"] < 0].copy()
    surpluses = data[data["project_wide_change"] > 0].copy()

    # Working copy to track remaining surplus
    sur = surpluses.copy()
    sur["__remain__"] = sur["project_wide_change"].astype(float)

    band_rank = {"Low": 1, "Medium": 2, "High": 3, "Very High": 4}
    
    # Sort deficits by distinctiveness rank (Very High > High > Medium > Low)
    sorted_deficits = sorted(deficits.iterrows(), 
                            key=lambda t: (-band_rank.get(str(t[1]["distinctiveness"]), 0), t[0]))
    
    # Track what each deficit received
    deficit_received = {}
    
    # Apply trading rules to offset deficits with surpluses
    for di, d in sorted_deficits:
        need = abs(float(d["project_wide_change"]))
        d_band = str(d["distinctiveness"])
        d_hab = clean_text(d.get("habitat", ""))
        
        deficit_key = (di, d_hab, d_band)
        deficit_received[deficit_key] = 0.0
        
        # Find eligible surpluses
        elig_idx = [si for si, s in sur.iterrows()
                    if can_offset_watercourse(d_band, d_hab,
                                             str(s["distinctiveness"]),
                                             clean_text(s.get("habitat", "")))
                    and sur.loc[si, "__remain__"] > 0]
        
        # Sort by priority: higher distinctiveness first, then larger surplus
        elig_idx = sorted(elig_idx,
                         key=lambda i: (-band_rank.get(str(sur.loc[i, "distinctiveness"]), 0),
                                       -sur.loc[i, "__remain__"]))
        
        # Allocate surpluses to deficit
        for i in elig_idx:
            if need <= 1e-9:
                break
            give = min(need, float(sur.loc[i, "__remain__"]))
            if give <= 0:
                continue
            sur.loc[i, "__remain__"] -= give
            deficit_received[deficit_key] += give
            need -= give

    # Calculate residual unmet deficits
    remaining_records = []
    
    for di, d in deficits.iterrows():
        d_hab = clean_text(d.get("habitat", ""))
        d_band = str(d["distinctiveness"])
        
        original_need = abs(float(d["project_wide_change"]))
        deficit_key = (di, d_hab, d_band)
        received = deficit_received.get(deficit_key, 0.0)
        unmet = max(original_need - received, 0.0)
        
        if unmet > 1e-4:  # Filter out floating-point errors
            remaining_records.append({
                "habitat": d_hab,
                "distinctiveness": d_band,
                "unmet_units_after_on_site_offset": round(unmet, 6)
            })

    # Detail table of remaining surpluses (for headline allocation)
    surplus_after_offsets_detail = sur.rename(columns={"__remain__": "surplus_remaining_units"})[
        ["habitat", "distinctiveness", "surplus_remaining_units"]
    ].copy()

    return {
        "residual_off_site": pd.DataFrame(remaining_records).reset_index(drop=True) if remaining_records else pd.DataFrame(columns=["habitat", "distinctiveness", "unmet_units_after_on_site_offset"]),
        "surplus_after_offsets_detail": surplus_after_offsets_detail
    }


def parse_headline_all_unit_types(xls: pd.ExcelFile) -> Dict[str, Dict[str, float]]:
    """
    Parse Headline Results for all unit types (Habitat, Hedgerow, Watercourse).
    Returns dict with keys: 'habitat', 'hedgerow', 'watercourse'
    Each value is a dict with keys: target_percent, baseline_units, units_required, unit_deficit
    """
    SHEET_NAME = "Headline Results"
    
    def extract_percent(val) -> Optional[float]:
        """Extract percentage from string like '10 %' or '15%'"""
        if val is None or (isinstance(val, float) and pd.isna(val)): 
            return None
        s = clean_text(str(val))
        num = pd.to_numeric(s.replace("%", "").strip(), errors="coerce")
        if pd.notna(num):
            return float(num / 100.0 if num > 1 else num)
        return None
    
    def extract_number(val) -> float:
        """Extract number from cell value"""
        if val is None or (isinstance(val, float) and pd.isna(val)): 
            return 0.0
        return float(pd.to_numeric(val, errors="coerce") or 0.0)
    
    # Default values if parsing fails
    defaults = {
        "habitat": {"target_percent": 0.10, "baseline_units": 0.0, "units_required": 0.0, "unit_deficit": 0.0},
        "hedgerow": {"target_percent": 0.10, "baseline_units": 0.0, "units_required": 0.0, "unit_deficit": 0.0},
        "watercourse": {"target_percent": 0.10, "baseline_units": 0.0, "units_required": 0.0, "unit_deficit": 0.0}
    }
    
    try:
        raw = pd.read_excel(xls, sheet_name=SHEET_NAME, header=None)
    except Exception:
        return defaults
    
    # Find header row
    header_idx = None
    for i in range(min(200, len(raw))):
        txt = " ".join([clean_text(x).lower() for x in raw.iloc[i].tolist()])
        if "unit type" in txt and ("target" in txt or "baseline" in txt):
            header_idx = i
            break
    
    if header_idx is None:
        return defaults
    
    df = raw.iloc[header_idx:].copy()
    df.columns = [clean_text(x) for x in df.iloc[0].tolist()]
    df = df.iloc[1:].reset_index(drop=True)
    
    # Normalize column names
    norm = {re.sub(r"[^a-z0-9]+", "_", c.lower()).strip("_"): c for c in df.columns}
    
    unit_col = next((norm[k] for k in ["unit_type", "type", "unit"] if k in norm), None)
    baseline_col = next((norm[k] for k in ["baseline_units", "baseline", "baseline_unit"] if k in norm), None)
    target_col = next((norm[k] for k in ["target", "target_percent", "target_"] if k in norm), None)
    required_col = next((norm[k] for k in ["units_required", "required", "unit_required"] if k in norm), None)
    deficit_col = next((norm[k] for k in ["unit_deficit", "deficit"] if k in norm), None)
    
    result = defaults.copy()
    
    # Parse each unit type
    for unit_type, patterns in [
        ("habitat", [r"\bhabi?tat\s*units?\b", r"\barea\s*habitat\s*units?\b"]),
        ("hedgerow", [r"\bhedgerow\s*units?\b"]),
        ("watercourse", [r"\bwatercourse\s*units?\b"])
    ]:
        def is_target_row(row) -> bool:
            if unit_col:
                val = clean_text(row.get(unit_col, "")).lower()
                for pattern in patterns:
                    if re.search(pattern, val):
                        return True
            # Also check in all row values
            row_text = " ".join([clean_text(v).lower() for v in row.tolist()])
            for pattern in patterns:
                if re.search(pattern, row_text):
                    return True
            return False
        
        mask = df.apply(is_target_row, axis=1)
        if not mask.any():
            continue
        
        row = df.loc[mask].iloc[0]
        
        # Extract values
        baseline_units = 0.0
        if baseline_col and baseline_col in row.index:
            baseline_units = extract_number(row[baseline_col])
        
        target_percent = 0.10  # default
        if target_col and target_col in row.index:
            pct = extract_percent(row[target_col])
            if pct is not None:
                target_percent = pct
        
        units_required = 0.0
        if required_col and required_col in row.index:
            units_required = extract_number(row[required_col])
        
        unit_deficit = 0.0
        if deficit_col and deficit_col in row.index:
            unit_deficit = extract_number(row[deficit_col])
        
        result[unit_type] = {
            "target_percent": target_percent,
            "baseline_units": baseline_units,
            "units_required": units_required,
            "unit_deficit": unit_deficit
        }
    
    return result


def parse_headline_target_row(xls: pd.ExcelFile, unit_type_keyword: str = "Area habitat units") -> Dict[str, float]:
    """
    Parse Headline Results for dynamic target %, baseline units.
    Returns dict with keys: target_percent, baseline_units
    
    DEPRECATED: Use parse_headline_all_unit_types() for comprehensive parsing
    """
    SHEET_NAME = "Headline Results"
    
    def extract_percent(val) -> Optional[float]:
        """Extract percentage from string like '10 %' or '15%'"""
        if val is None or (isinstance(val, float) and pd.isna(val)): 
            return None
        s = clean_text(str(val))
        num = pd.to_numeric(s.replace("%", "").strip(), errors="coerce")
        if pd.notna(num):
            return float(num / 100.0 if num > 1 else num)
        return None
    
    try:
        raw = pd.read_excel(xls, sheet_name=SHEET_NAME, header=None)
    except Exception:
        return {"target_percent": 0.10, "baseline_units": 0.0}
    
    # Find header row
    header_idx = None
    for i in range(min(200, len(raw))):
        txt = " ".join([clean_text(x).lower() for x in raw.iloc[i].tolist()])
        if "unit type" in txt and ("target" in txt or "baseline" in txt):
            header_idx = i
            break
    
    if header_idx is None:
        return {"target_percent": 0.10, "baseline_units": 0.0}
    
    df = raw.iloc[header_idx:].copy()
    df.columns = [clean_text(x) for x in df.iloc[0].tolist()]
    df = df.iloc[1:].reset_index(drop=True)
    
    # Normalize column names
    norm = {re.sub(r"[^a-z0-9]+", "_", c.lower()).strip("_"): c for c in df.columns}
    
    unit_col = next((norm[k] for k in ["unit_type", "type", "unit"] if k in norm), None)
    baseline_col = next((norm[k] for k in ["baseline_units", "baseline", "baseline_unit"] if k in norm), None)
    target_col = next((norm[k] for k in ["target", "target_percent", "target_"] if k in norm), None)
    
    # Find the area habitat units row
    def is_target_row(row) -> bool:
        if unit_col:
            val = clean_text(row.get(unit_col, "")).lower()
            if re.search(r"\barea\s*habitat\s*units\b", val):
                return True
        return re.search(r"\barea\s*habitat\s*units\b", " ".join([clean_text(v).lower() for v in row.tolist()])) is not None
    
    mask = df.apply(is_target_row, axis=1)
    if not mask.any():
        return {"target_percent": 0.10, "baseline_units": 0.0}
    
    row = df.loc[mask].iloc[0]
    
    # Extract values
    baseline_units = 0.0
    if baseline_col and baseline_col in row.index:
        baseline_units = float(pd.to_numeric(row[baseline_col], errors="coerce") or 0.0)
    
    target_percent = 0.10  # default
    if target_col and target_col in row.index:
        pct = extract_percent(row[target_col])
        if pct is not None:
            target_percent = pct
    
    return {
        "target_percent": target_percent,
        "baseline_units": baseline_units
    }


def allocate_to_headline(
    remaining_target: float,
    surplus_detail: pd.DataFrame
) -> float:
    """
    Allocate available surpluses to cover headline net gain target.
    Returns total amount applied to headline.
    """
    if remaining_target <= 1e-9:
        return 0.0
    
    band_rank = {"Very High": 4, "High": 3, "Medium": 2, "Low": 1}
    
    # Sort surpluses by rank (higher first), then by remaining units (larger first)
    surs = surplus_detail.copy()
    surs["surplus_remaining_units"] = pd.to_numeric(surs["surplus_remaining_units"], errors="coerce").fillna(0.0)
    surs = surs[surs["surplus_remaining_units"] > 1e-9]
    surs["__rank__"] = surs["distinctiveness"].map(lambda b: band_rank.get(str(b), 0))
    surs = surs.sort_values(by=["__rank__", "surplus_remaining_units"], ascending=[False, False])
    
    to_cover = remaining_target
    
    for _, s in surs.iterrows():
        if to_cover <= 1e-9:
            break
        give = min(to_cover, float(s["surplus_remaining_units"]))
        if give <= 1e-9:
            continue
        to_cover -= give
    
    total_applied = remaining_target - to_cover
    return total_applied


def parse_metric_requirements(uploaded_file) -> Dict:
    """
    Main entry point: parse a BNG metric file and return OFF-SITE mitigation requirements.
    
    This follows the metric reader logic exactly:
    1. Parse Trading Summary sheets
    2. Apply on-site offsets with trading rules:
       - Area habitats: Medium hierarchy, broad group matching
       - Hedgerows: Distinctiveness-based (Very High/High = like-for-like; Medium/Low/Very Low = same or better)
    3. Parse headline Net Gain target from Headline Results
    4. Allocate remaining surpluses to headline
    5. Return residual off-site requirements AND remaining surplus
    
    Returns dict with keys: 
    - 'area': DataFrame with columns: habitat, units
    - 'hedgerows': DataFrame with columns: habitat, units
    - 'watercourses': DataFrame with columns: habitat, units
    - 'baseline_info': Dict with keys 'habitat', 'hedgerow', 'watercourse'
        Each containing: target_percent, baseline_units, units_required, unit_deficit
    - 'surplus': DataFrame with columns: habitat, broad_group, distinctiveness, units_surplus
        Contains remaining surplus after offsetting deficits and headline
    - 'flow_log': List of allocation records from on-site offset processing
        Each record has: deficit_habitat, deficit_broad_group, deficit_distinctiveness,
        surplus_habitat, surplus_broad_group, surplus_distinctiveness, 
        units_allocated, priority_medium
    
    For area: returns combined residual (habitat deficits + headline remainder after on-site offsets)
    For hedgerows: returns residual (hedgerow deficits + headline remainder after on-site offsets)
        Hedgerow trading rules: Very High/High = like-for-like; Medium/Low/Very Low = same distinctiveness or better
    For watercourses: returns raw deficits + headline net gain requirement
        (no trading rules applied for watercourses)
    
    Note: Medium distinctiveness deficits are now processed with priority hierarchy:
    Priority groups (first): Cropland, Lakes, Sparsely vegetated land, Urban, 
                            Individual trees, Woodland and forest, Intertidal sediment,
                            Intertidal hard structures
    Secondary groups (after): Grassland, Heathland and shrub
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
        "Trading Summary WaterC's",  # Handle apostrophe variation
        "Trading Summary Watercourses",
        "Watercourses Trading Summary",
        "Trading Summary (Watercourses)"
    ]
    
    # Parse each category
    area_norm, _, _ = normalise_requirements(xls, AREA_SHEETS, "Area Habitats")
    hedge_norm, _, _ = normalise_requirements(xls, HEDGE_SHEETS, "Hedgerows")
    water_norm, _, _ = normalise_requirements(xls, WATER_SHEETS, "Watercourses")
    
    # Parse headline baseline info for all unit types
    headline_all = parse_headline_all_unit_types(xls)
    
    # ========== AREA HABITATS - Full trading logic ==========
    area_requirements = []
    surplus_after_all_offsets = pd.DataFrame()
    area_flow_log = []
    
    if not area_norm.empty:
        # Step 1: Apply on-site offsets
        alloc = apply_area_offsets(area_norm)
        residual_table = alloc["residual_off_site"]
        surplus_detail = alloc["surplus_after_offsets_detail"]
        area_flow_log = alloc.get("flow_log", [])
        
        # Add habitat residuals
        if not residual_table.empty:
            for _, row in residual_table.iterrows():
                area_requirements.append({
                    "habitat": clean_text(row["habitat"]),
                    "units": float(row["unmet_units_after_on_site_offset"])
                })
        
        # Step 2: Parse headline target
        habitat_info = headline_all["habitat"]
        target_pct = habitat_info["target_percent"]
        baseline_units = habitat_info["baseline_units"]
        headline_requirement = baseline_units * target_pct
        
        # Step 3: Allocate surpluses to headline (track what's used)
        # Make a copy to track remaining surplus after headline allocation
        surplus_remaining = surplus_detail.copy()
        surplus_remaining["surplus_remaining_units"] = pd.to_numeric(
            surplus_remaining["surplus_remaining_units"], errors="coerce"
        ).fillna(0.0)
        
        # Allocate to headline
        band_rank = {"Very High": 4, "High": 3, "Medium": 2, "Low": 1}
        surs = surplus_remaining.copy()
        surs = surs[surs["surplus_remaining_units"] > 1e-9]
        surs["__rank__"] = surs["distinctiveness"].map(lambda b: band_rank.get(str(b), 0))
        surs = surs.sort_values(by=["__rank__", "surplus_remaining_units"], ascending=[False, False])
        
        to_cover = headline_requirement
        for idx, s in surs.iterrows():
            if to_cover <= 1e-9:
                break
            give = min(to_cover, float(s["surplus_remaining_units"]))
            if give <= 1e-9:
                continue
            surplus_remaining.loc[idx, "surplus_remaining_units"] -= give
            to_cover -= give
        
        applied_to_headline = headline_requirement - to_cover
        
        # Step 4: Calculate headline remainder
        residual_headline = max(headline_requirement - applied_to_headline, 0.0)
        
        # Add headline remainder if > 0
        # Use "Net Gain (Low-equivalent)" to match optimiser's naming
        if residual_headline > 1e-9:
            area_requirements.append({
                "habitat": "Net Gain (Low-equivalent)",
                "units": round(residual_headline, 4)
            })
        
        # Keep only non-zero surplus
        surplus_after_all_offsets = surplus_remaining[
            surplus_remaining["surplus_remaining_units"] > 1e-9
        ].rename(columns={"surplus_remaining_units": "units_surplus"}).copy()
    
    # ========== HEDGEROWS - Full trading logic ==========
    hedge_requirements = []
    if not hedge_norm.empty:
        # Step 1: Apply on-site offsets
        hedge_alloc = apply_hedgerow_offsets(hedge_norm)
        hedge_residual_table = hedge_alloc["residual_off_site"]
        hedge_surplus_detail = hedge_alloc["surplus_after_offsets_detail"]
        
        # Add hedgerow residuals after on-site offsetting
        if not hedge_residual_table.empty:
            for _, row in hedge_residual_table.iterrows():
                hedge_requirements.append({
                    "habitat": clean_text(row["habitat"]),
                    "units": float(row["unmet_units_after_on_site_offset"])
                })
        
        # Step 2: Parse headline target
        hedgerow_info = headline_all["hedgerow"]
        hedge_target_pct = hedgerow_info["target_percent"]
        hedge_baseline_units = hedgerow_info["baseline_units"]
        hedge_net_gain_requirement = hedge_baseline_units * hedge_target_pct
        
        # Step 3: Allocate remaining surpluses to headline
        hedge_surplus_remaining = hedge_surplus_detail.copy()
        hedge_surplus_remaining["surplus_remaining_units"] = pd.to_numeric(
            hedge_surplus_remaining["surplus_remaining_units"], errors="coerce"
        ).fillna(0.0)
        
        # Allocate to headline
        band_rank = {"Very Low": 0, "Low": 1, "Medium": 2, "High": 3, "Very High": 4}
        hedge_surs = hedge_surplus_remaining.copy()
        hedge_surs = hedge_surs[hedge_surs["surplus_remaining_units"] > 1e-9]
        hedge_surs["__rank__"] = hedge_surs["distinctiveness"].map(lambda b: band_rank.get(str(b), 0))
        hedge_surs = hedge_surs.sort_values(by=["__rank__", "surplus_remaining_units"], ascending=[False, False])
        
        hedge_to_cover = hedge_net_gain_requirement
        for idx, s in hedge_surs.iterrows():
            if hedge_to_cover <= 1e-9:
                break
            give = min(hedge_to_cover, float(s["surplus_remaining_units"]))
            if give <= 1e-9:
                continue
            hedge_surplus_remaining.loc[idx, "surplus_remaining_units"] -= give
            hedge_to_cover -= give
        
        hedge_applied_to_headline = hedge_net_gain_requirement - hedge_to_cover
        
        # Step 4: Calculate headline remainder
        hedge_residual_headline = max(hedge_net_gain_requirement - hedge_applied_to_headline, 0.0)
        
        # Add headline remainder if > 0
        if hedge_residual_headline > 1e-9:
            hedge_requirements.append({
                "habitat": "Net Gain (Hedgerows)",
                "units": round(hedge_residual_headline, 4)
            })
    else:
        # No hedgerow trading data, just add net gain if baseline exists
        hedgerow_info = headline_all["hedgerow"]
        hedge_net_gain_requirement = hedgerow_info["baseline_units"] * hedgerow_info["target_percent"]
        
        if hedge_net_gain_requirement > 1e-9:
            hedge_requirements.append({
                "habitat": "Net Gain (Hedgerows)",
                "units": round(hedge_net_gain_requirement, 4)
            })
    
    # ========== WATERCOURSES - Full trading logic ==========
    water_requirements = []
    water_diagnostics = {
        "raw_data": water_norm.copy() if not water_norm.empty else pd.DataFrame(),
        "surpluses": pd.DataFrame(),
        "deficits": pd.DataFrame(),
        "net_gain_requirement": 0.0,
        "net_gain_applied": 0.0
    }
    
    if not water_norm.empty:
        # Step 1: Apply on-site offsets with watercourse trading rules
        water_alloc = apply_watercourse_offsets(water_norm)
        water_residual_table = water_alloc["residual_off_site"]
        water_surplus_detail = water_alloc["surplus_after_offsets_detail"]
        
        # Store diagnostics: surpluses after on-site offsets
        water_diagnostics["surpluses"] = water_surplus_detail.copy()
        water_diagnostics["deficits"] = water_residual_table.copy()
        
        # Add watercourse residuals after on-site offsetting
        if not water_residual_table.empty:
            for _, row in water_residual_table.iterrows():
                water_requirements.append({
                    "habitat": clean_text(row["habitat"]),
                    "units": float(row["unmet_units_after_on_site_offset"])
                })
        
        # Step 2: Parse headline target
        watercourse_info = headline_all["watercourse"]
        water_target_pct = watercourse_info["target_percent"]
        water_baseline_units = watercourse_info["baseline_units"]
        water_net_gain_requirement = water_baseline_units * water_target_pct
        
        water_diagnostics["net_gain_requirement"] = water_net_gain_requirement
        
        # Step 3: Allocate remaining surpluses to headline
        water_surplus_remaining = water_surplus_detail.copy()
        water_surplus_remaining["surplus_remaining_units"] = pd.to_numeric(
            water_surplus_remaining["surplus_remaining_units"], errors="coerce"
        ).fillna(0.0)
        
        # Add debug as warning so it appears in Streamlit
        import warnings
        warnings.warn(f"WATERCOURSE DEBUG: {len(water_surplus_remaining)} surplus rows before allocation", UserWarning)
        for idx, row in water_surplus_remaining.iterrows():
            warnings.warn(f"  - {row.get('habitat', 'N/A')} | Dist: '{row.get('distinctiveness', 'N/A')}' | Units: {row.get('surplus_remaining_units', 0):.6f}", UserWarning)
        
        # Allocate to headline
        band_rank = {"Low": 1, "Medium": 2, "High": 3, "Very High": 4}
        water_surs = water_surplus_remaining.copy()
        water_surs = water_surs[water_surs["surplus_remaining_units"] > 1e-9]
        
        warnings.warn(f"WATERCOURSE DEBUG: After filtering: {len(water_surs)} rows", UserWarning)
        
        water_surs["__rank__"] = water_surs["distinctiveness"].map(lambda b: band_rank.get(str(b), 0))
        
        for idx, row in water_surs.iterrows():
            warnings.warn(f"  - {row.get('habitat', 'N/A')} | Dist: '{row.get('distinctiveness', 'N/A')}' | Rank: {row.get('__rank__', 'N/A')} | Units: {row.get('surplus_remaining_units', 0):.6f}", UserWarning)
        
        water_surs = water_surs.sort_values(by=["__rank__", "surplus_remaining_units"], ascending=[False, False])
        
        warnings.warn(f"WATERCOURSE DEBUG: Net Gain requirement: {water_net_gain_requirement:.6f}", UserWarning)
        
        water_to_cover = water_net_gain_requirement
        for idx, s in water_surs.iterrows():
            if water_to_cover <= 1e-9:
                break
            give = min(water_to_cover, float(s["surplus_remaining_units"]))
            if give <= 1e-9:
                continue
            warnings.warn(f"  - Allocating {give:.6f} from {s.get('habitat', 'N/A')}", UserWarning)
            water_surplus_remaining.loc[idx, "surplus_remaining_units"] -= give
            water_to_cover -= give
        
        water_applied_to_headline = water_net_gain_requirement - water_to_cover
        warnings.warn(f"WATERCOURSE DEBUG: Applied: {water_applied_to_headline:.6f}, Remaining: {water_to_cover:.6f}", UserWarning)
        
        # Store diagnostic info
        water_diagnostics["net_gain_applied"] = water_applied_to_headline
        
        # Step 4: Calculate headline remainder
        water_residual_headline = max(water_net_gain_requirement - water_applied_to_headline, 0.0)
        
        # Add headline remainder if > 0
        if water_residual_headline > 1e-9:
            water_requirements.append({
                "habitat": "Net Gain (Watercourses)",
                "units": round(water_residual_headline, 4)
            })
    else:
        # No watercourse trading data, just add net gain if baseline exists
        watercourse_info = headline_all["watercourse"]
        water_net_gain_requirement = watercourse_info["baseline_units"] * watercourse_info["target_percent"]
        
        if water_net_gain_requirement > 1e-9:
            water_requirements.append({
                "habitat": "Net Gain (Watercourses)",
                "units": round(water_net_gain_requirement, 4)
            })
    
    return {
        "area": pd.DataFrame(area_requirements) if area_requirements else pd.DataFrame(columns=["habitat", "units"]),
        "hedgerows": pd.DataFrame(hedge_requirements) if hedge_requirements else pd.DataFrame(columns=["habitat", "units"]),
        "watercourses": pd.DataFrame(water_requirements) if water_requirements else pd.DataFrame(columns=["habitat", "units"]),
        "baseline_info": headline_all,
        "surplus": surplus_after_all_offsets if not surplus_after_all_offsets.empty else pd.DataFrame(columns=["habitat", "broad_group", "distinctiveness", "units_surplus"]),
        "flow_log": area_flow_log,
        "watercourse_diagnostics": water_diagnostics
    }
