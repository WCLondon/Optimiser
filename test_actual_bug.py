"""
Test to actually reproduce the bug and find where it's happening
"""
import pandas as pd
from optimizer_core import prepare_options, prepare_hedgerow_options, prepare_watercourse_options

# Simulate backend with Ditches as Watercourse
backend = {
    "Banks": pd.DataFrame([
        {"bank_id": "BANK1", "bank_name": "Mansfield", "lpa_name": "Test LPA", "nca_name": "Test NCA", "BANK_KEY": "WC1P4B"}
    ]),
    "HabitatCatalog": pd.DataFrame([
        {"habitat_name": "Ditches", "broader_type": "", "distinctiveness_name": "Medium", "UmbrellaType": "Watercourse"},
        {"habitat_name": "Grassland - Traditional orchards", "broader_type": "Grassland", "distinctiveness_name": "High", "UmbrellaType": "Area Habitat"},
        {"habitat_name": "Grassland - Other neutral grassland", "broader_type": "Grassland", "distinctiveness_name": "Medium", "UmbrellaType": "Area Habitat"},
    ]),
    "Stock": pd.DataFrame([
        {"habitat_name": "Grassland - Traditional orchards", "stock_id": "S1", "bank_id": "BANK1", "quantity_available": 10.0, "BANK_KEY": "WC1P4B"},
        {"habitat_name": "Grassland - Other neutral grassland", "stock_id": "S2", "bank_id": "BANK1", "quantity_available": 10.0, "BANK_KEY": "WC1P4B"},
        {"habitat_name": "Ditches", "stock_id": "S3", "bank_id": "BANK1", "quantity_available": 10.0, "BANK_KEY": "WC1P4B"},
    ]),
    "Pricing": pd.DataFrame([
        {"habitat_name": "Grassland - Traditional orchards", "contract_size": "small", "tier": "adjacent", "bank_id": "BANK1", "BANK_KEY": "WC1P4B", "price": 32000},
        {"habitat_name": "Grassland - Other neutral grassland", "contract_size": "small", "tier": "adjacent", "bank_id": "BANK1", "BANK_KEY": "WC1P4B", "price": 22000},
        {"habitat_name": "Ditches", "contract_size": "small", "tier": "adjacent", "bank_id": "BANK1", "BANK_KEY": "WC1P4B", "price": 75000},
    ]),
    "TradingRules": pd.DataFrame(),
    "DistinctivenessLevels": pd.DataFrame([
        {"distinctiveness_name": "Low", "level_value": 1},
        {"distinctiveness_name": "Medium", "level_value": 2},
        {"distinctiveness_name": "High", "level_value": 3},
    ])
}

# Demand with Ditches
demand_df = pd.DataFrame([
    {"habitat_name": "Ditches", "units_required": 0.657}
])

print("="*80)
print("ACTUAL BUG REPRODUCTION TEST")
print("="*80)
print("\nBackend setup:")
print(f"  - Ditches: UmbrellaType='Watercourse'")
print(f"  - Grassland habitats: UmbrellaType='Area Habitat'")
print(f"\nDemand: Ditches (0.657 units)")
print("\n" + "="*80)

# Call prepare_options (area ledger) - should return ZERO options for Ditches
print("\n1. Testing prepare_options (AREA LEDGER):")
print("-" * 80)
try:
    options_area, caps_area, bk_area = prepare_options(
        demand_df=demand_df,
        chosen_size="small",
        target_lpa="Test LPA",
        target_nca="Test NCA",
        lpa_neigh=[],
        nca_neigh=[],
        lpa_neigh_norm=[],
        nca_neigh_norm=[],
        backend=backend
    )
    
    print(f"Options created: {len(options_area)}")
    if len(options_area) == 0:
        print("✅ CORRECT: No options created for Ditches in area ledger")
    else:
        print(f"❌ BUG FOUND: {len(options_area)} options created for Ditches!")
        for opt in options_area:
            print(f"   - Type: {opt['type']}, Supply: {opt['supply_habitat']}, Demand: {opt['demand_habitat']}")
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Call prepare_watercourse_options - should return options for Ditches
print("\n2. Testing prepare_watercourse_options (WATERCOURSE LEDGER):")
print("-" * 80)
try:
    options_water, caps_water, bk_water = prepare_watercourse_options(
        demand_df=demand_df,
        chosen_size="small",
        target_lpa="Test LPA",
        target_nca="Test NCA",
        lpa_neigh=[],
        nca_neigh=[],
        lpa_neigh_norm=[],
        nca_neigh_norm=[],
        backend=backend
    )
    
    print(f"Options created: {len(options_water)}")
    if len(options_water) > 0:
        print("✅ CORRECT: Options created for Ditches in watercourse ledger")
        for opt in options_water[:3]:  # Show first 3
            print(f"   - Type: {opt['type']}, Supply: {opt['supply_habitat']}, Demand: {opt['demand_habitat']}")
    else:
        print(f"⚠️  WARNING: No options created in watercourse ledger")
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("CONCLUSION:")
if len(options_area) == 0:
    print("✅ Bug is NOT in prepare_options - it correctly filters Ditches")
    print("   The issue must be elsewhere (deployment, caching, or different data)")
else:
    print("❌ Bug IS in prepare_options - it's creating options for Ditches!")
    print("   Need to debug the filtering logic")
print("="*80)
