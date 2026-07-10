terraform {
  required_version = ">= 1.8"
}

resource "aws_s3_bucket" "build_logs" {
  bucket = "synthetic-checkout-build-logs"
}

output "artifact_bucket_name" {
  value = aws_s3_bucket.artifacts.bucket
}
