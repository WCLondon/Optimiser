"""
Test to verify that Ditches demand does NOT create options in area ledger
"""
import pandas as pd
from optimizer_core import prepare_options

# Create mock backend
backend = {
    "Banks": pd.DataFrame([
        {"bank_id": "BANK1", "bank_name": "Test Bank", "lpa_name": "Test LPA", "nca_name": "Test NCA", "BANK_KEY": "BANK1"}
    ]),
    "HabitatCatalog": pd.DataFrame([
        {"habitat_name": "Ditches", "broader_type": "", "distinctiveness_name": "Medium", "UmbrellaType": "Watercourse"},
        {"habitat_name": "Grassland - Traditional orchards", "broader_type": "Grassland", "distinctiveness_name": "High", "UmbrellaType": "Area Habitat"},
    ]),
    "Stock": pd.DataFrame([
        {"habitat_name": "Grassland - Traditional orchards", "stock_id": "S1", "bank_id": "BANK1", "quantity_available": 10.0, "BANK_KEY": "BANK1"}
    ]),
    "Pricing": pd.DataFrame([
        {"habitat_name": "Grassland - Traditional orchards", "contract_size": "small", "tier": "local", "bank_id": "BANK1", "BANK_KEY": "BANK1", "price": 30000}
    ]),
    "TradingRules": pd.DataFrame(),
    "DistinctivenessLevels": pd.DataFrame([
        {"distinctiveness_name": "Low", "level_value": 1},
        {"distinctiveness_name": "Medium", "level_value": 2},
        {"distinctiveness_name": "High", "level_value": 3},
    ])
}

# Create demand with ONLY Ditches (watercourse demand)
demand_df = pd.DataFrame([
    {"habitat_name": "Ditches", "units_required": 0.657}
])

print("="*80)
print("TEST: Ditches demand in prepare_options (area ledger)")
print("="*80)
print(f"\nDemand: Ditches (UmbrellaType='Watercourse'), 0.657 units")
print(f"Available stock: Grassland - Traditional orchards (UmbrellaType='Area Habitat'), 10.0 units")
print()

# Call prepare_options (area ledger)
options, caps, bk = prepare_options(
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

print(f"Options created by prepare_options (area ledger): {len(options)}")
print()

if len(options) == 0:
    print("✅ PASS: No options created for Ditches demand in area ledger")
    print("   Ditches was correctly filtered out!")
else:
    print(f"❌ FAIL: {len(options)} options created for Ditches demand in area ledger")
    print("   This is CROSS-LEDGER TRADING!")
    print("\nOptions created:")
    for opt in options:
        print(f"  - Demand: {opt['demand_habitat']}, Supply: {opt['supply_habitat']}, Type: {opt['type']}")

print("="*80)
