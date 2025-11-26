#!/usr/bin/env python3
"""
Script to add Cypher Carbon Brokers individual user logins to the introducers table.

This script adds individual logins for Cypher employees.
Each user gets their own username (email) and password with proper hashing.
All users are linked to the parent 'Cypher' promoter for discount settings.

Password format: [Firstname][Lastname]1
Note: These are initial passwords as specified by the administrator.
Users should be encouraged to change their password on first login using
the "Change Password" feature in the sidebar.

Usage:
    python add_cypher_users.py

Note: Requires database connection configured in .streamlit/secrets.toml
"""

import sys
from database import SubmissionsDB

# List of Cypher users to add
# Initial passwords follow the format [Firstname][Lastname]1 as requested by admin.
# Users should change their password on first login.
CYPHER_USERS = [
    {"name": "Charlie Cliff", "username": "charlie@cyphercarbonbrokers.co.uk", "password": "CharlieCliff1"},
    {"name": "Henry Cowls", "username": "henry.cowls@cypherclimatebrokers.co.uk", "password": "HenryCowls1"},
]

# Parent promoter name - all child accounts inherit discount settings from this
PARENT_PROMOTER_NAME = "Cypher"


def ensure_parent_promoter_exists():
    """Ensure the parent Cypher promoter exists, create if needed."""
    db = SubmissionsDB()
    
    parent = db.get_introducer_by_name(PARENT_PROMOTER_NAME)
    if parent:
        return parent['id'], parent
    
    # Create parent Cypher promoter with no discount (can be updated later by admin)
    print(f"Creating parent promoter '{PARENT_PROMOTER_NAME}'...")
    parent_id = db.add_introducer(
        name=PARENT_PROMOTER_NAME,
        discount_type='no_discount',
        discount_value=0,
        username=None,  # Parent account doesn't need login
        password=None,
        parent_introducer_id=None
    )
    print(f"✓ Created parent promoter: {PARENT_PROMOTER_NAME} (ID: {parent_id})")
    
    parent = db.get_introducer_by_id(parent_id)
    return parent_id, parent


def add_cypher_users():
    """Add all Cypher users to the database as child accounts of Cypher promoter."""
    db = SubmissionsDB()
    
    print("Adding Cypher individual user logins...")
    print("-" * 60)
    
    # Ensure parent Cypher promoter exists
    parent_id, parent = ensure_parent_promoter_exists()
    
    parent_discount_type = parent.get('discount_type', 'no_discount')
    parent_discount_value = parent.get('discount_value', 0)
    
    print(f"✓ Using parent promoter: {PARENT_PROMOTER_NAME} (ID: {parent_id})")
    print(f"  Discount: {parent_discount_type} = {parent_discount_value}")
    print("-" * 60)
    
    success_count = 0
    error_count = 0
    
    for user in CYPHER_USERS:
        try:
            # Check if user already exists by username
            existing = db.get_introducer_by_username(user["username"])
            if existing:
                print(f"⚠️  User already exists: {user['name']} ({user['username']})")
                continue
            
            # Check if user exists by name
            existing_by_name = db.get_introducer_by_name(user["name"])
            if existing_by_name:
                # Update existing user with credentials and parent link
                db.set_introducer_credentials(
                    existing_by_name["id"],
                    user["username"],
                    user["password"]
                )
                print(f"✓  Updated credentials for: {user['name']} ({user['username']})")
                success_count += 1
                continue
            
            # Add new user as child of Cypher
            # Child accounts use 'no_discount' as their own type since they inherit from parent
            introducer_id = db.add_introducer(
                name=user["name"],
                discount_type='no_discount',  # Will inherit from parent
                discount_value=0,
                username=user["username"],
                password=user["password"],
                parent_introducer_id=parent_id  # Link to Cypher
            )
            print(f"✓  Added: {user['name']} ({user['username']}) - ID: {introducer_id}, Parent: {parent_id}")
            success_count += 1
            
        except Exception as e:
            print(f"✗  Error adding {user['name']}: {e}")
            error_count += 1
    
    print("-" * 60)
    print(f"Summary: {success_count} users added/updated, {error_count} errors")
    
    return success_count, error_count


def verify_users():
    """Verify that all users were added correctly."""
    db = SubmissionsDB()
    
    print("\nVerifying Cypher users...")
    print("-" * 60)
    
    for user in CYPHER_USERS:
        introducer = db.get_introducer_by_username(user["username"])
        if introducer:
            has_password = bool(introducer.get("password_hash") and introducer.get("password_salt"))
            has_parent = bool(introducer.get("parent_introducer_id"))
            status = "✓ OK" if (has_password and has_parent) else "⚠️ Incomplete"
            parent_info = f", Parent ID: {introducer.get('parent_introducer_id')}" if has_parent else ", No parent"
            print(f"{status}: {user['name']} ({user['username']}){parent_info}")
        else:
            print(f"✗ Missing: {user['name']} ({user['username']})")


if __name__ == "__main__":
    try:
        success, errors = add_cypher_users()
        verify_users()
        
        if errors > 0:
            sys.exit(1)
        sys.exit(0)
        
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
