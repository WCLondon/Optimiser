"""
Database module for BNG Optimiser submissions tracking.
Uses SQLite for local storage of all form submissions and optimization results.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd


class SubmissionsDB:
    """Handle all database operations for submissions tracking."""
    
    def __init__(self, db_path: str = "submissions.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self._conn = None
        self._init_database()
    
    def _get_connection(self):
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return self._conn
    
    def _init_database(self):
        """Create tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Main submissions table
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    submission_date TEXT NOT NULL,
                    
                    -- Client details
                    client_name TEXT,
                    reference_number TEXT,
                    site_location TEXT,
                    
                    -- Location metadata
                    target_lpa TEXT,
                    target_nca TEXT,
                    target_lat REAL,
                    target_lon REAL,
                    lpa_neighbors TEXT,
                    nca_neighbors TEXT,
                    
                    -- Form inputs (demand)
                    demand_habitats TEXT,
                    
                    -- Optimization metadata
                    contract_size TEXT,
                    total_cost REAL,
                    admin_fee REAL,
                    total_with_admin REAL,
                    num_banks_selected INTEGER,
                    banks_used TEXT,
                    
                    -- Manual entries
                    manual_hedgerow_entries TEXT,
                    manual_watercourse_entries TEXT,
                    
                    -- Full allocation results (JSON)
                    allocation_results TEXT,
                    
                    -- User info
                    username TEXT,
                    
                    -- Promoter/Introducer info
                    promoter_name TEXT,
                    promoter_discount_type TEXT,
                    promoter_discount_value REAL
                )
        """)
        
        # Allocations detail table (normalized)
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS allocation_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    submission_id INTEGER NOT NULL,
                    
                    -- Allocation specifics
                    bank_key TEXT,
                    bank_name TEXT,
                    demand_habitat TEXT,
                    supply_habitat TEXT,
                    allocation_type TEXT,
                    tier TEXT,
                    units_supplied REAL,
                    unit_price REAL,
                    cost REAL,
                    
                    FOREIGN KEY (submission_id) REFERENCES submissions(id)
                )
        """)
        
        # Introducers/Promoters table
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS introducers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    discount_type TEXT NOT NULL CHECK(discount_type IN ('tier_up', 'percentage')),
                    discount_value REAL NOT NULL,
                    created_date TEXT NOT NULL,
                    updated_date TEXT NOT NULL
                )
        """)
        
        conn.commit()
        
    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def store_submission(self, 
                        client_name: str,
                        reference_number: str,
                        site_location: str,
                        target_lpa: str,
                        target_nca: str,
                        target_lat: Optional[float],
                        target_lon: Optional[float],
                        lpa_neighbors: List[str],
                        nca_neighbors: List[str],
                        demand_df: pd.DataFrame,
                        allocation_df: pd.DataFrame,
                        contract_size: str,
                        total_cost: float,
                        admin_fee: float,
                        manual_hedgerow_rows: List[Dict],
                        manual_watercourse_rows: List[Dict],
                        username: str = "",
                        promoter_name: Optional[str] = None,
                        promoter_discount_type: Optional[str] = None,
                        promoter_discount_value: Optional[float] = None) -> int:
        """
        Store a complete submission to the database.
        Returns the submission_id for reference.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Prepare data
        submission_date = datetime.now().isoformat()
        total_with_admin = total_cost + admin_fee
        
        # Banks used
        banks_used = allocation_df["BANK_KEY"].unique().tolist() if not allocation_df.empty else []
        num_banks = len(banks_used)
        
        # Convert lists/dicts to JSON
        lpa_neighbors_json = json.dumps(lpa_neighbors)
        nca_neighbors_json = json.dumps(nca_neighbors)
        demand_habitats_json = demand_df.to_json(orient='records') if not demand_df.empty else "[]"
        banks_used_json = json.dumps(banks_used)
        manual_hedgerow_json = json.dumps(manual_hedgerow_rows)
        manual_watercourse_json = json.dumps(manual_watercourse_rows)
        allocation_results_json = allocation_df.to_json(orient='records') if not allocation_df.empty else "[]"
        
        # Insert main submission
        cursor.execute("""
            INSERT INTO submissions (
                submission_date, client_name, reference_number, site_location,
                target_lpa, target_nca, target_lat, target_lon,
                lpa_neighbors, nca_neighbors, demand_habitats,
                contract_size, total_cost, admin_fee, total_with_admin,
                num_banks_selected, banks_used,
                manual_hedgerow_entries, manual_watercourse_entries,
                allocation_results, username,
                promoter_name, promoter_discount_type, promoter_discount_value
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            submission_date, client_name, reference_number, site_location,
            target_lpa, target_nca, target_lat, target_lon,
            lpa_neighbors_json, nca_neighbors_json, demand_habitats_json,
            contract_size, total_cost, admin_fee, total_with_admin,
            num_banks, banks_used_json,
            manual_hedgerow_json, manual_watercourse_json,
            allocation_results_json, username,
            promoter_name, promoter_discount_type, promoter_discount_value
        ))
        
        submission_id = cursor.lastrowid
        
        # Insert allocation details
        if not allocation_df.empty:
            for _, row in allocation_df.iterrows():
                cursor.execute("""
                    INSERT INTO allocation_details (
                        submission_id, bank_key, bank_name,
                        demand_habitat, supply_habitat, allocation_type,
                        tier, units_supplied, unit_price, cost
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                submission_id,
                    row.get("BANK_KEY", ""),
                    row.get("bank_name", ""),
                    row.get("demand_habitat", ""),
                    row.get("supply_habitat", ""),
                    row.get("allocation_type", ""),
                    row.get("proximity", ""),
                    row.get("units_supplied", 0.0),
                    row.get("unit_price", 0.0),
                    row.get("cost", 0.0)
                ))
        
        conn.commit()
        return submission_id
    
    def get_all_submissions(self, limit: Optional[int] = None) -> pd.DataFrame:
        """Get all submissions as a DataFrame."""
        query = "SELECT * FROM submissions ORDER BY submission_date DESC"
        if limit:
            query += f" LIMIT {limit}"
        
        conn = self._get_connection()
        df = pd.read_sql_query(query, conn)
        return df
    
    def get_submission_by_id(self, submission_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific submission by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,))
        row = cursor.fetchone()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def get_allocations_for_submission(self, submission_id: int) -> pd.DataFrame:
        """Get allocation details for a specific submission."""
        conn = self._get_connection()
        df = pd.read_sql_query(
            "SELECT * FROM allocation_details WHERE submission_id = ?",
            conn,
            params=(submission_id,)
        )
        return df
    
    def filter_submissions(self,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          client_name: Optional[str] = None,
                          lpa: Optional[str] = None,
                          nca: Optional[str] = None,
                          reference_number: Optional[str] = None) -> pd.DataFrame:
        """Filter submissions based on various criteria."""
        query = "SELECT * FROM submissions WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND submission_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND submission_date <= ?"
            params.append(end_date)
        
        if client_name:
            query += " AND client_name LIKE ?"
            params.append(f"%{client_name}%")
        
        if lpa:
            query += " AND target_lpa LIKE ?"
            params.append(f"%{lpa}%")
        
        if nca:
            query += " AND target_nca LIKE ?"
            params.append(f"%{nca}%")
        
        if reference_number:
            query += " AND reference_number LIKE ?"
            params.append(f"%{reference_number}%")
        
        query += " ORDER BY submission_date DESC"
        
        conn = self._get_connection()
        df = pd.read_sql_query(query, conn, params=params)
        return df
    
    def export_to_csv(self, df: pd.DataFrame, filename: str = "submissions_export.csv") -> bytes:
        """Export DataFrame to CSV bytes for download."""
        return df.to_csv(index=False).encode('utf-8')
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics about submissions."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Total submissions
        cursor.execute("SELECT COUNT(*) FROM submissions")
        total_submissions = cursor.fetchone()[0]
        
        # Total revenue
        cursor.execute("SELECT SUM(total_with_admin) FROM submissions")
        total_revenue = cursor.fetchone()[0] or 0.0
        
        # Most common LPAs
        cursor.execute("""
            SELECT target_lpa, COUNT(*) as count 
            FROM submissions 
            WHERE target_lpa IS NOT NULL AND target_lpa != ''
            GROUP BY target_lpa 
            ORDER BY count DESC 
            LIMIT 5
        """)
        top_lpas = cursor.fetchall()
        
        # Most common clients
        cursor.execute("""
            SELECT client_name, COUNT(*) as count 
            FROM submissions 
            WHERE client_name IS NOT NULL AND client_name != ''
            GROUP BY client_name 
            ORDER BY count DESC 
            LIMIT 5
        """)
        top_clients = cursor.fetchall()
        
        return {
            "total_submissions": total_submissions,
            "total_revenue": total_revenue,
            "top_lpas": top_lpas,
            "top_clients": top_clients
        }
    
    # ================= Introducers/Promoters CRUD =================
    
    def add_introducer(self, name: str, discount_type: str, discount_value: float) -> int:
        """Add a new introducer/promoter."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO introducers (name, discount_type, discount_value, created_date, updated_date)
            VALUES (?, ?, ?, ?, ?)
        """, (name, discount_type, discount_value, now, now))
        
        conn.commit()
        return cursor.lastrowid
    
    def get_all_introducers(self) -> List[Dict[str, Any]]:
        """Get all introducers."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM introducers ORDER BY name")
        rows = cursor.fetchall()
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def get_introducer_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get an introducer by name."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM introducers WHERE name = ?", (name,))
        row = cursor.fetchone()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def update_introducer(self, introducer_id: int, name: str, discount_type: str, discount_value: float):
        """Update an existing introducer."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute("""
            UPDATE introducers 
            SET name = ?, discount_type = ?, discount_value = ?, updated_date = ?
            WHERE id = ?
        """, (name, discount_type, discount_value, now, introducer_id))
        
        conn.commit()
    
    def delete_introducer(self, introducer_id: int):
        """Delete an introducer."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM introducers WHERE id = ?", (introducer_id,))
        
        conn.commit()
