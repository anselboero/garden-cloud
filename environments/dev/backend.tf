terraform {
    backend "gcs" {
        bucket = "anselboero-website-dev-tfstate"
    }
}