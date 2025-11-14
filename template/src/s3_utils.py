"""
S3 utilities for loading CVM sections and documents from AWS S3.
"""
import os
import json
import boto3
import tempfile
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

class S3FileLoader:
    """Utility class for loading files from S3 with local caching."""
    
    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        """
        Initialize S3 file loader.
        
        Args:
            bucket_name: Name of the S3 bucket
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self._cache = {}
    
    def load_json_from_s3(self, s3_key: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Load JSON file from S3.
        
        Args:
            s3_key: S3 object key
            use_cache: Whether to use local cache
            
        Returns:
            Parsed JSON data or None if error
        """
        if use_cache and s3_key in self._cache:
            logger.info(f"Using cached data for {s3_key}")
            return self._cache[s3_key]
        
        try:
            logger.info(f"Loading JSON from S3: s3://{self.bucket_name}/{s3_key}")
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)
            
            if use_cache:
                self._cache[s3_key] = data
                logger.info(f"Cached data for {s3_key}")
            
            return data
            
        except ClientError as e:
            logger.error(f"Error loading JSON from S3: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading JSON from S3: {e}")
            return None
    
    def load_text_from_s3(self, s3_key: str, use_cache: bool = True) -> Optional[str]:
        """
        Load text file from S3.
        
        Args:
            s3_key: S3 object key
            use_cache: Whether to use local cache
            
        Returns:
            Text content or None if error
        """
        if use_cache and s3_key in self._cache:
            logger.info(f"Using cached text data for {s3_key}")
            return self._cache[s3_key]
        
        try:
            logger.info(f"Loading text from S3: s3://{self.bucket_name}/{s3_key}")
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response['Body'].read().decode('utf-8')
            
            if use_cache:
                self._cache[s3_key] = content
                logger.info(f"Cached text data for {s3_key}")
            
            return content
            
        except ClientError as e:
            logger.error(f"Error loading text from S3: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading text from S3: {e}")
            return None
    
    def download_file_from_s3(self, s3_key: str, local_path: str) -> bool:
        """
        Download file from S3 to local path.
        
        Args:
            s3_key: S3 object key
            local_path: Local file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Downloading file from S3: s3://{self.bucket_name}/{s3_key} -> {local_path}")
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            logger.info(f"Successfully downloaded file to {local_path}")
            return True
            
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading file from S3: {e}")
            return False
    
    def clear_cache(self):
        """Clear the local cache."""
        self._cache.clear()
        logger.info("Cache cleared")

# Global instance
_s3_loader = None

def get_s3_loader() -> S3FileLoader:
    """Get the global S3 loader instance."""
    global _s3_loader
    if _s3_loader is None:
        # Get bucket name from environment or use default
        bucket_name = os.getenv('S3_DOCUMENTS_BUCKET', 'streamlit-fastapi-documents-32142665')
        region = os.getenv('AWS_REGION', 'us-east-1')
        _s3_loader = S3FileLoader(bucket_name, region)
    return _s3_loader

def load_cvm_sections() -> Optional[Dict[str, Any]]:
    """
    Load CVM sections JSON from S3.
    
    Returns:
        CVM sections data or None if error
    """
    s3_loader = get_s3_loader()
    return s3_loader.load_json_from_s3('cvm_sections/Cvm175Sections.json')

def load_cvm_text() -> Optional[str]:
    """
    Load CVM text content from S3.
    
    Returns:
        CVM text content or None if error
    """
    s3_loader = get_s3_loader()
    return s3_loader.load_text_from_s3('cvm_sections/resol175consolid.txt')

def get_article_by_id(article_id: str) -> Optional[Dict[str, Any]]:
    """
    Get specific article data by ID.
    
    Args:
        article_id: Article ID (e.g., 'artigo93')
        
    Returns:
        Article data or None if not found
    """
    articles_data = load_cvm_sections()
    if not articles_data:
        return None
    
    for article in articles_data:
        if article.get('article_id') == article_id:
            return article
    
    return None

def get_article_content(article_data: Dict[str, Any]) -> Optional[str]:
    """
    Get article content from text file.
    
    Args:
        article_data: Article metadata with start_offset and end_offset
        
    Returns:
        Article content or None if error
    """
    if not article_data:
        return None
    
    text_content = load_cvm_text()
    if not text_content:
        return None
    
    start_offset = article_data.get('start_offset', 0)
    end_offset = article_data.get('end_offset', len(text_content))
    
    return text_content[start_offset:end_offset].strip()
