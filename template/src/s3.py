import io
import boto3
from botocore.client import Config

from src.settings import settings
from datetime import datetime

import json

DEFAULT_S3_KEY_TEMPLATE = {
    "llm-report-templates": "{template_type}/{template_name}/{timestamp}.json"
}

class S3Client:
    def __init__(self, bucket_name, key_template=DEFAULT_S3_KEY_TEMPLATE):
        self.bucket_name = bucket_name + settings.bucket_suffix
        self.key_template = key_template
        if settings.environment == "development":
            storage_options = {
                "environment": "development",
                "key": settings.minio_root_user,
                "secret": settings.minio_root_password,
                "token": None,
                "bucket_name": self.bucket_name,
                "region": settings.region,
                "endpoint_url": "http://minio:9000"
            }

            self.s3_client = boto3.client(
                "s3",
                endpoint_url=storage_options.get("endpoint_url", "http://localhost:9000"),
                aws_access_key_id=storage_options["key"],
                aws_secret_access_key=storage_options["secret"],
                config=Config(signature_version='s3v4'),
                region_name=storage_options.get("region", "us-east-1")
            )
        else:
            sts_client = boto3.client("sts")
            assumed_role = sts_client.assume_role(
                RoleArn=settings.streamlit_role_arn,
                RoleSessionName="streamlit"
            )
            credentials = assumed_role["Credentials"]

            storage_options = {
                "environment": settings.environment,
                "key": credentials["AccessKeyId"],
                "secret": credentials["SecretAccessKey"],
                "token": credentials["SessionToken"],
                "bucket_name": self.bucket_name,
                "region": settings.region,
                "endpoint_url": None
            }

            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=storage_options["key"],
                aws_secret_access_key=storage_options["secret"],
                region_name=storage_options["region"]
            )

            print("Started S3 client: ", settings.storage_options)
    
    def parse_file_object(self, data, format):
        if format == 'json':
            bytes_buffer = io.BytesIO()
            bytes_buffer.write(json.dumps(data).encode("utf-8"))
            bytes_buffer.seek(0)  
        else:
            bytes_buffer = io.BytesIO()
        
        return bytes_buffer
        
    def upload(self, data, format, file_metadata):
        key = self.key_template.get(self.bucket_name).format(timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")).format(file_metadata)
        file_bytes = self.parse_file_object(data, format)
        try:
            self.s3_client.upload_fileobj(file_bytes, self.storage_options["bucket_name"], key)
            print(f"✅ Upload successful: {key}.pdf")
            return True
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            return False
