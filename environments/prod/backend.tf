terraform {
    backend "gcs" {
        bucket = "anselboero-website-prod-tfstate"
    }
}