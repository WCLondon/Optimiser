"""
Demonstration script for Sales & Quotes CSV generation.

This script shows example output from the CSV generation feature.
"""

from datetime import datetime
import pandas as pd
from sales_quotes_csv import (
    generate_sales_quotes_csv,
    generate_sales_quotes_csv_from_optimizer_output
)


def demo_single_allocation():
    """Demonstrate CSV generation for a single allocation."""
    print("=" * 80)
    print("DEMO 1: Single Allocation (Non-Paired, Adjacent Tier)")
    print("=" * 80)
    
    allocations = [{
        "bank_ref": "WC1P2",
        "bank_name": "Nunthorpe",
        "is_paired": False,
        "spatial_relation": "adjacent",
        "spatial_multiplier_numeric": 4.0/3.0,
        "allocation_total_credits": 10.5,
        "contract_value_gbp": 15000.0,
        "habitats": [
            {
                "type": "Grassland - Other neutral grassland",
                "units_supplied": 10.0,
                "effective_units": 13.33,
                "avg_effective_unit_price": 1125.0
            }
        ]
    }]
    
    csv_output = generate_sales_quotes_csv(
        quote_number="1923",
        client_name="David Evans",
        development_address="123 High Street, London",
        base_ref="BNG01640",
        introducer="John Smith",
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Westminster",
        national_character_area="Thames Valley",
        allocations=allocations,
        contract_size="small"
    )
    
    print("\nCSV Output:")
    print(csv_output)
    print("\nKey Points:")
    print("- Ref: BNG01640 (no suffix for single allocation)")
    print("- Spatial Multiplier: =4/3 (formula for adjacent, non-paired)")
    print("- Notes: (blank for non-paired)")
    print("- Habitat 1 Type: Grassland - Other neutral grassland")
    print("- Habitat 1 # credits: 10.0 (uses units_supplied for non-paired)")
    print("- Habitat 1 Quoted Price: 1125.0")
    print()


def demo_multi_allocation():
    """Demonstrate CSV generation for multiple allocations with ref suffixing."""
    print("=" * 80)
    print("DEMO 2: Multi-Bank Allocations (Ref Suffixing a, b, c...)")
    print("=" * 80)
    
    allocations = [
        {
            "bank_ref": "WC1P2",
            "bank_name": "Nunthorpe",
            "is_paired": False,
            "spatial_relation": "adjacent",
            "spatial_multiplier_numeric": 4.0/3.0,
            "allocation_total_credits": 10.0,
            "contract_value_gbp": 10000.0,
            "habitats": [{
                "type": "Grassland",
                "units_supplied": 10.0,
                "effective_units": 13.33,
                "avg_effective_unit_price": 750.0
            }]
        },
        {
            "bank_ref": "WC2P3",
            "bank_name": "Oakwood",
            "is_paired": False,
            "spatial_relation": "far",
            "spatial_multiplier_numeric": 2.0,
            "allocation_total_credits": 5.0,
            "contract_value_gbp": 5000.0,
            "habitats": [{
                "type": "Woodland",
                "units_supplied": 5.0,
                "effective_units": 10.0,
                "avg_effective_unit_price": 500.0
            }]
        }
    ]
    
    csv_output = generate_sales_quotes_csv(
        quote_number="1924",
        client_name="Jane Doe",
        development_address="456 Another Street, Cambridge",
        base_ref="BNG01641",
        introducer=None,
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Camden",
        national_character_area="London Basin",
        allocations=allocations,
        contract_size="medium"
    )
    
    print("\nCSV Output:")
    for i, line in enumerate(csv_output.strip().split('\n'), 1):
        print(f"Row {i}: {line[:120]}...")
    
    print("\nKey Points:")
    print("- First allocation ref: BNG01641a")
    print("- Second allocation ref: BNG01641b")
    print("- Introducer: Direct (default when None)")
    print()


def demo_paired_allocation():
    """Demonstrate CSV generation for paired allocations with SRM notes."""
    print("=" * 80)
    print("DEMO 3: Paired Allocation (Multi-Bank Solution)")
    print("=" * 80)
    
    allocations = [{
        "bank_ref": "WC1P2",
        "bank_name": "Nunthorpe",
        "is_paired": True,
        "spatial_relation": "far",
        "spatial_multiplier_numeric": 1.0,
        "allocation_total_credits": 10.0,
        "contract_value_gbp": 10000.0,
        "habitats": [{
            "type": "Grassland",
            "units_supplied": 10.0,
            "effective_units": 10.0,
            "avg_effective_unit_price": 1000.0
        }]
    }]
    
    csv_output = generate_sales_quotes_csv(
        quote_number="1925",
        client_name="Test Client",
        development_address="Test Address, Bristol",
        base_ref="BNG01642",
        introducer="Test Introducer",
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Bristol",
        national_character_area="Severn Vale",
        allocations=allocations,
        contract_size="small"
    )
    
    print("\nCSV Output:")
    print(csv_output[:120] + "...")
    
    print("\nKey Points:")
    print("- is_paired: True")
    print("- spatial_relation: far")
    print("- Notes: 'SRM manual (0.5)' (for paired + far)")
    print("- Spatial Multiplier: 1 (numeric for paired)")
    print("- Habitat # credits: 10.0 (uses effective_units for paired)")
    print()


def demo_multiple_habitats():
    """Demonstrate CSV generation with multiple habitats."""
    print("=" * 80)
    print("DEMO 4: Multiple Habitats (up to 8)")
    print("=" * 80)
    
    # Create 3 different habitats
    habitats = [
        {
            "type": "Grassland - Other neutral grassland",
            "units_supplied": 5.0,
            "effective_units": 6.67,
            "avg_effective_unit_price": 1000.0
        },
        {
            "type": "Heathland and shrub - Mixed scrub",
            "units_supplied": 3.0,
            "effective_units": 4.0,
            "avg_effective_unit_price": 1200.0
        },
        {
            "type": "Woodland - Other woodland",
            "units_supplied": 2.0,
            "effective_units": 2.67,
            "avg_effective_unit_price": 1500.0
        }
    ]
    
    allocations = [{
        "bank_ref": "WC1P2",
        "bank_name": "Nunthorpe",
        "is_paired": False,
        "spatial_relation": "adjacent",
        "spatial_multiplier_numeric": 4.0/3.0,
        "allocation_total_credits": 10.0,
        "contract_value_gbp": 12000.0,
        "habitats": habitats
    }]
    
    csv_output = generate_sales_quotes_csv(
        quote_number="1926",
        client_name="Multi Habitat Client",
        development_address="Multi Site Address",
        base_ref="BNG01643",
        introducer="Multi Introducer",
        today_date=datetime(2025, 11, 10),
        local_planning_authority="Test LPA",
        national_character_area="Test NCA",
        allocations=allocations,
        contract_size="small"
    )
    
    print(f"\nGenerated {len(csv_output)} bytes of CSV data")
    print("\nKey Points:")
    print("- 3 habitats included in single allocation")
    print("- Habitat 1: Grassland - Other neutral grassland (5.0 units, £1000)")
    print("- Habitat 2: Heathland and shrub - Mixed scrub (3.0 units, £1200)")
    print("- Habitat 3: Woodland - Other woodland (2.0 units, £1500)")
    print("- Each habitat occupies 7 columns (Type, # credits, ST, Std Price, Quoted Price, Min, Price inc SM)")
    print("- Only Type, # credits, and Quoted Price are populated")
    print()


def demo_from_dataframe():
    """Demonstrate CSV generation from optimizer DataFrame output."""
    print("=" * 80)
    print("DEMO 5: Generate from Optimizer DataFrame")
    print("=" * 80)
    
    # Create a sample allocation DataFrame (simulating optimizer output)
    alloc_df = pd.DataFrame([
        {
            "BANK_KEY": "WC1P2",
            "bank_name": "Nunthorpe",
            "allocation_type": "normal",
            "tier": "adjacent",
            "supply_habitat": "Grassland - Other neutral grassland",
            "units_supplied": 10.0,
            "unit_price": 1000.0,
            "cost": 10000.0
        }
    ])
    
    csv_output = generate_sales_quotes_csv_from_optimizer_output(
        quote_number="1927",
        client_name="DataFrame Client",
        development_address="DataFrame Address",
        base_ref="BNG01644",
        introducer="DataFrame Introducer",
        today_date=datetime(2025, 11, 10),
        local_planning_authority="DataFrame LPA",
        national_character_area="DataFrame NCA",
        alloc_df=alloc_df,
        contract_size="small"
    )
    
    print("\nCSV Output:")
    print(csv_output[:120] + "...")
    
    print("\nKey Points:")
    print("- Automatically converts optimizer DataFrame to CSV format")
    print("- Groups allocations by bank")
    print("- Calculates spatial multiplier from tier")
    print("- Determines paired status from allocation_type")
    print()


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "SALES & QUOTES CSV GENERATION DEMO" + " " * 24 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")
    
    demo_single_allocation()
    demo_multi_allocation()
    demo_paired_allocation()
    demo_multiple_habitats()
    demo_from_dataframe()
    
    print("=" * 80)
    print("DEMOS COMPLETE")
    print("=" * 80)
    print("\nThe CSV output is ready to paste into the Sales & Quotes Excel workbook.")
    print("Each row represents one bank allocation, with columns A-CY (103 columns total).")
    print("\nColumn Structure:")
    print("  A: (blank)")
    print("  B: Client Name")
    print("  C: Development Address")
    print("  D: Reference Number (with a,b,c suffix for multi-allocations)")
    print("  ...")
    print("  AC: Habitat Bank / Source")
    print("  AD: Spatial Multiplier (formula for non-paired, 1 for paired)")
    print("  ...")
    print("  AV-BB: Habitat 1 (Type, # credits, Quoted Price)")
    print("  BC-BI: Habitat 2")
    print("  BJ-BP: Habitat 3")
    print("  BQ-BW: Habitat 4")
    print("  BX-CD: Habitat 5")
    print("  CE-CK: Habitat 6")
    print("  CL-CR: Habitat 7")
    print("  CS-CY: Habitat 8")
    print()
