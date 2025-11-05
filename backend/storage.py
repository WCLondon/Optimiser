"""
Supabase Storage integration for file uploads
"""

import os
from typing import Optional
from datetime import datetime, timedelta
from supabase import create_client, Client

from config import get_settings


class SupabaseStorage:
    """Handle file uploads and signed URL generation for Supabase Storage"""
    
    def __init__(self):
        settings = get_settings()
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        self.metrics_bucket = settings.supabase_metrics_bucket
        self.pdfs_bucket = settings.supabase_pdfs_bucket
    
    async def upload_metric(self, file_content: bytes, filename: str) -> str:
        """
        Upload metric file to Supabase storage
        
        Args:
            file_content: File content as bytes
            filename: Destination filename
        
        Returns:
            Storage path to the uploaded file
        """
        path = f"metrics/{filename}"
        
        # Upload to Supabase storage
        response = self.client.storage.from_(self.metrics_bucket).upload(
            path=path,
            file=file_content,
            file_options={
                "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "x-upsert": "false"  # Don't overwrite existing files
            }
        )
        
        return path
    
    async def upload_pdf(self, file_content: bytes, filename: str) -> str:
        """
        Upload PDF file to Supabase storage
        
        Args:
            file_content: File content as bytes
            filename: Destination filename
        
        Returns:
            Storage path to the uploaded file
        """
        path = f"pdfs/{filename}"
        
        # Upload to Supabase storage
        response = self.client.storage.from_(self.pdfs_bucket).upload(
            path=path,
            file=file_content,
            file_options={
                "content-type": "application/pdf",
                "x-upsert": "false"
            }
        )
        
        return path
    
    async def get_signed_url(self, path: str, expires_in: int = 3600) -> str:
        """
        Generate a signed URL for file access
        
        Args:
            path: Storage path to the file
            expires_in: Expiration time in seconds (default 1 hour)
        
        Returns:
            Signed URL string
        """
        # Determine which bucket based on path
        bucket = self.metrics_bucket if path.startswith("metrics/") else self.pdfs_bucket
        
        # Generate signed URL
        response = self.client.storage.from_(bucket).create_signed_url(
            path=path,
            expires_in=expires_in
        )
        
        return response['signedURL']
    
    async def delete_file(self, path: str) -> bool:
        """
        Delete a file from storage
        
        Args:
            path: Storage path to the file
        
        Returns:
            True if deleted successfully
        """
        bucket = self.metrics_bucket if path.startswith("metrics/") else self.pdfs_bucket
        
        try:
            self.client.storage.from_(bucket).remove([path])
            return True
        except Exception as e:
            print(f"Error deleting file {path}: {str(e)}")
            return False
