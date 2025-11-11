"""
Simple test to verify Ditches filtering logic
"""
import pandas as pd

def sstr(x):
    if x is None:
        return ''
    return str(x).strip()

# Simulate the filtering logic
Catalog = pd.DataFrame([
    {"habitat_name": "Ditches", "broader_type": "", "distinctiveness_name": "Medium", "UmbrellaType": "Watercourse"},
    {"habitat_name": "Grassland", "broader_type": "Grassland", "distinctiveness_name": "High", "UmbrellaType": "Area Habitat"},
])

# Normalize UmbrellaType
Catalog['UmbrellaType'] = Catalog['UmbrellaType'].map(sstr)

print("="*80)
print("TEST: Would Ditches be skipped in prepare_options?")
print("="*80)

dem_hab = "Ditches"
print(f"\nTesting demand: '{dem_hab}'")

# Simulate the filter logic from prepare_options line 1724-1734
if "UmbrellaType" in Catalog.columns:
    cat_match = Catalog[Catalog["habitat_name"].astype(str).str.strip() == dem_hab.strip()]
    print(f"Found in catalog: {not cat_match.empty}")
    if not cat_match.empty:
        umb = sstr(cat_match.iloc[0]["UmbrellaType"]).strip().lower()
        print(f"UmbrellaType: '{umb}'")
        if umb == "hedgerow" or umb == "watercourse":
            print(f"\n✅ WOULD BE SKIPPED: UmbrellaType == '{umb}'")
            print("   Ditches will NOT create options in area ledger!")
        else:
            print(f"\n❌ WOULD NOT BE SKIPPED: UmbrellaType '{umb}' is not hedgerow/watercourse")
            print("   Ditches WOULD create options in area ledger (BUG!)")
    else:
        print("\n❌ Not found in catalog - would NOT be skipped")
else:
    print("\n❌ UmbrellaType column doesn't exist")

print("="*80)
