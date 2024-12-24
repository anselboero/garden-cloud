locals {
    env = "prod"
}

provider "google" {
    project = "${var.project}"
}

module "cloud_run_functions" {
  source  = "../../modules/cloud_run_functions"
  project = "${var.project}"
}