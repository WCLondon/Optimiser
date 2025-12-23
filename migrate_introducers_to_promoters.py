#!/usr/bin/env python3
"""
Migration script to populate promoter_companies and promoter_individuals tables
from existing introducers table.

This script is optional and only needed if you want to migrate existing introducer data
to the new promoter system.
"""

import sys
from database import SubmissionsDB
from sqlalchemy import text

def migrate_introducers_to_promoters():
    """Migrate data from introducers table to new promoter tables."""
    print("=" * 60)
    print("Introducer to Promoter Migration Script")
    print("=" * 60)
    
    try:
        db = SubmissionsDB()
        engine = db._get_connection()
        
        print("\n1. Checking existing introducers...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM introducers"))
            count = result.fetchone()[0]
            print(f"   Found {count} introducers in old table")
            
            if count == 0:
                print("\n   No introducers to migrate. Exiting.")
                return True
        
        print("\n2. Starting migration...")
        print("   Note: This will create company entries for each introducer")
        print("   and individual entries with the same credentials")
        
        with engine.connect() as conn:
            # Fetch all introducers
            result = conn.execute(text("""
                SELECT id, name, username, password_hash, password_salt, 
                       discount_type, discount_value, created_date, updated_date
                FROM introducers
                ORDER BY id
            """))
            introducers = result.fetchall()
            
            migrated = 0
            skipped = 0
            
            for intro in introducers:
                intro_dict = dict(intro._mapping)
                
                # Generate UUIDs for new system
                import uuid
                company_id = str(uuid.uuid4())
                individual_id = str(uuid.uuid4())
                
                try:
                    trans = conn.begin()
                    
                    # Check if company already exists
                    check = conn.execute(text("""
                        SELECT id FROM promoter_companies WHERE name = :name
                    """), {"name": intro_dict['name']})
                    
                    existing_company = check.fetchone()
                    
                    if existing_company:
                        print(f"   ⚠ Skipping {intro_dict['name']} - company already exists")
                        skipped += 1
                        trans.rollback()
                        continue
                    
                    # Create company
                    conn.execute(text("""
                        INSERT INTO promoter_companies 
                        (id, name, discount_type, discount_value, active, type,
                         requires_approval, approval_threshold, created_date, updated_date)
                        VALUES (:id, :name, :discount_type, :discount_value, TRUE, 'Company',
                                FALSE, 0.0, :created_date, :updated_date)
                    """), {
                        "id": company_id,
                        "name": intro_dict['name'],
                        "discount_type": intro_dict['discount_type'] or 'no_discount',
                        "discount_value": intro_dict['discount_value'] or 0,
                        "created_date": intro_dict['created_date'],
                        "updated_date": intro_dict['updated_date']
                    })
                    
                    # Create individual if username exists
                    if intro_dict['username']:
                        # Convert password from salt+hash to plain SHA256
                        # Note: This requires re-hashing. Existing users will need to reset passwords
                        # or we need the original passwords (which we don't have)
                        
                        # For now, we'll set a placeholder hash that won't work
                        # Users will need to reset their passwords
                        placeholder_hash = "0" * 64  # Invalid hash
                        
                        conn.execute(text("""
                            INSERT INTO promoter_individuals
                            (id, name, username, password_hash, company_id, active, type,
                             role, created_date, updated_date)
                            VALUES (:id, :name, :username, :password_hash, :company_id, TRUE, 'User',
                                    'Admin', :created_date, :updated_date)
                        """), {
                            "id": individual_id,
                            "name": intro_dict['name'],
                            "username": intro_dict['username'],
                            "password_hash": placeholder_hash,
                            "company_id": company_id,
                            "created_date": intro_dict['created_date'],
                            "updated_date": intro_dict['updated_date']
                        })
                        
                        print(f"   ✓ Migrated {intro_dict['name']} (company + individual)")
                        print(f"     ⚠ Password needs to be reset for username: {intro_dict['username']}")
                    else:
                        print(f"   ✓ Migrated {intro_dict['name']} (company only)")
                    
                    trans.commit()
                    migrated += 1
                    
                except Exception as e:
                    trans.rollback()
                    print(f"   ✗ Error migrating {intro_dict['name']}: {e}")
                    skipped += 1
        
        print("\n" + "=" * 60)
        print("Migration Summary:")
        print(f"  - {migrated} introducers migrated successfully")
        print(f"  - {skipped} introducers skipped")
        print("\nIMPORTANT:")
        print("  - Users with usernames will need to RESET their passwords")
        print("  - The old password hashing system (SHA256+salt) is incompatible")
        print("  - The new system uses plain SHA256 hashing")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n⚠ WARNING: This migration script is for reference only!")
    print("The new promoter tables should be populated directly from Supabase.")
    print("This script is only useful if you have data in the old 'introducers' table")
    print("that you want to migrate.\n")
    
    response = input("Do you want to proceed with migration? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        success = migrate_introducers_to_promoters()
        sys.exit(0 if success else 1)
    else:
        print("\nMigration cancelled.")
        sys.exit(0)
