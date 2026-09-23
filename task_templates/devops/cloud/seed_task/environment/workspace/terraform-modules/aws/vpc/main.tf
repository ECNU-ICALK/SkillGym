# TODO: build the shared Terraform VPC module here by factoring the existing
# local Terraform execution model into a reusable module.
#
# Preserve the current local execution model:
# - keep the module providerless and locally plannable
# - centralize shared naming, tagging and topology logic in the module
