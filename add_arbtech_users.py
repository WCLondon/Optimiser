#!/usr/bin/env python3
"""
Script to add Arbtech individual user logins to the introducers table.

This script adds 14 individual logins for Arbtech promoter ecologists.
Each user gets their own username (email) and password with proper hashing.
All users are linked to the parent 'Arbtech' promoter for discount settings.

Password format: [Firstname][Lastname]1
Note: These are initial passwords as specified by the administrator.
Users should be encouraged to change their password on first login using
the "Change Password" feature in the sidebar.

Usage:
    python add_arbtech_users.py

Note: Requires database connection configured in .streamlit/secrets.toml
"""

import sys
from database import SubmissionsDB

# List of Arbtech users to add
# Initial passwords follow the format [Firstname][Lastname]1 as requested by admin.
# Users should change their password on first login.
ARBTECH_USERS = [
    {"name": "Beth Ellison-Perrett", "username": "Bethellison-perrett@arbtech.co.uk", "password": "BethEllison-Perrett1"},
    {"name": "Craig Williams", "username": "Craigwilliams@arbtech.co.uk", "password": "CraigWilliams1"},
    {"name": "Fay Brotherhood", "username": "Faybrotherhood@arbtech.co.uk", "password": "FayBrotherhood1"},
    {"name": "Georgina Rennie", "username": "Georginarennie@arbtech.co.uk", "password": "GeorginaRennie1"},
    {"name": "Harley Stone", "username": "Harleystone@arbtech.co.uk", "password": "HarleyStone1"},
    {"name": "Harry Brindle", "username": "Harrybrindle@arbtech.co.uk", "password": "HarryBrindle1"},
    {"name": "Jamie-Lee Anderson", "username": "Jamie-leeanderson@arbtech.co.uk", "password": "Jamie-LeeAnderson1"},
    {"name": "Jeremy Grout", "username": "Jeremygrout@arbtech.co.uk", "password": "JeremyGrout1"},
    {"name": "Jonathan Stuttard", "username": "Jonathanstuttard@arbtech.co.uk", "password": "JonathanStuttard1"},
    {"name": "Leo Plevin", "username": "Leoplevin@arbtech.co.uk", "password": "LeoPlevin1"},
    {"name": "Kelly Clarke", "username": "Kellyclarke@arbtech.co.uk", "password": "KellyClarke1"},
    {"name": "Natalie Evans", "username": "Natalieevans@arbtech.co.uk", "password": "NatalieEvans1"},
    {"name": "Robbie Mackenzie", "username": "Robbiemackenzie@arbtech.co.uk", "password": "RobbieMackenzie1"},
    {"name": "Viktoria Kossmann", "username": "Viktoriakossmann@arbtech.co.uk", "password": "ViktoriaKossmann1"},
]

# Parent promoter name - all child accounts inherit discount settings from this
PARENT_PROMOTER_NAME = "Arbtech"


def add_arbtech_users():
    """Add all Arbtech users to the database as child accounts of Arbtech promoter."""
    db = SubmissionsDB()
    
    print("Adding Arbtech individual user logins...")
    print("-" * 60)
    
    # First, get the parent Arbtech promoter ID
    parent = db.get_introducer_by_name(PARENT_PROMOTER_NAME)
    if not parent:
        print(f"✗ Error: Parent promoter '{PARENT_PROMOTER_NAME}' not found in database!")
        print("  Please ensure Arbtech is already in the introducers table.")
        return 0, 1
    
    parent_id = parent['id']
    parent_discount_type = parent.get('discount_type', 'no_discount')
    parent_discount_value = parent.get('discount_value', 0)
    
    print(f"✓ Found parent promoter: {PARENT_PROMOTER_NAME} (ID: {parent_id})")
    print(f"  Discount: {parent_discount_type} = {parent_discount_value}")
    print("-" * 60)
    
    success_count = 0
    error_count = 0
    
    for user in ARBTECH_USERS:
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
            
            # Add new user as child of Arbtech
            # Child accounts use 'no_discount' as their own type since they inherit from parent
            introducer_id = db.add_introducer(
                name=user["name"],
                discount_type='no_discount',  # Will inherit from parent
                discount_value=0,
                username=user["username"],
                password=user["password"],
                parent_introducer_id=parent_id  # Link to Arbtech
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
    
    print("\nVerifying Arbtech users...")
    print("-" * 60)
    
    for user in ARBTECH_USERS:
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
        success, errors = add_arbtech_users()
        verify_users()
        
        if errors > 0:
            sys.exit(1)
        sys.exit(0)
        
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
