# Infrastructure reference investigation

1. Identify the undeclared reference and the Terraform module or file that declares related resources.
2. Confirm whether the resource was renamed, moved to another module, or intentionally removed.
3. Propose the smallest reviewable configuration correction.
4. Do not run `terraform apply`, create cloud resources, or claim that infrastructure changed.
