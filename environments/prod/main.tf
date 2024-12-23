locals {
    env = "prod"
}

provider "google" {
    project = "${var.project}"
}