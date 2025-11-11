"""
Comprehensive diagnostic to trace why Ditches might create area habitat options
"""
import pandas as pd
import sys

def sstr(x):
    if x is None:
        return ''
    return str(x).strip()

print("="*80)
print("DIAGNOSTIC: Tracing Ditches through prepare_options filtering")
print("="*80)
print()

# Test data - simulate what should be in the database
Catalog = pd.DataFrame([
    {"habitat_name": "Ditches", "broader_type": "", "distinctiveness_name": "Medium", "UmbrellaType": "Watercourse"},
    {"habitat_name": "Grassland - Traditional orchards", "broader_type": "Grassland", "distinctiveness_name": "High", "UmbrellaType": "Area Habitat"},
])

# Normalize UmbrellaType (as done in prepare_options)
Catalog['UmbrellaType'] = Catalog['UmbrellaType'].map(sstr)

demand_df = pd.DataFrame([
    {"habitat_name": "Ditches", "units_required": 0.657}
])

print("1. CATALOG CONTENT:")
print(Catalog[['habitat_name', 'UmbrellaType']])
print()

print("2. DEMAND:")
print(demand_df)
print()

print("3. DEMAND FILTERING (lines 1724-1734 in prepare_options):")
print("-" * 80)

for di, drow in demand_df.iterrows():
    dem_hab = sstr(drow["habitat_name"])
    print(f"Processing demand: '{dem_hab}'")
    
    # Exact logic from prepare_options
    if "UmbrellaType" in Catalog.columns:
        print(f"  ✓ UmbrellaType column exists")
        cat_match = Catalog[Catalog["habitat_name"].astype(str).str.strip() == dem_hab.strip()]
        print(f"  Catalog lookup for '{dem_hab.strip()}': {len(cat_match)} rows found")
        
        if not cat_match.empty:
            print(f"  ✓ Habitat found in catalog")
            umb = sstr(cat_match.iloc[0]["UmbrellaType"]).strip().lower()
            print(f"  UmbrellaType value: '{umb}'")
            print(f"  Check: umb == 'hedgerow' -> {umb == 'hedgerow'}")
            print(f"  Check: umb == 'watercourse' -> {umb == 'watercourse'}")
            
            if umb == "hedgerow" or umb == "watercourse":
                print(f"  ✅ WOULD SKIP: Demand is {umb}, not an area habitat")
                print(f"  => NO OPTIONS CREATED for this demand")
            else:
                print(f"  ❌ WOULD NOT SKIP: UmbrellaType '{umb}' doesn't match hedgerow or watercourse")
                print(f"  => OPTIONS WOULD BE CREATED (CROSS-LEDGER BUG!)")
        else:
            print(f"  ⚠️  Habitat NOT found in catalog")
            print(f"  => WOULD NOT SKIP (would process as area habitat)")
    else:
        print(f"  ⚠️  UmbrellaType column does NOT exist")
        print(f"  => Would use keyword fallback")
    
    print()

print("="*80)
print("EXPECTED RESULT:")
print("  Ditches (UmbrellaType='Watercourse') should be SKIPPED")
print("  NO area habitat options should be created for Ditches")
print("="*80)
