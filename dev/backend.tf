terraform {
    backend "gcs" {
        bucket = "anselboero-website-dev-tfstate"
        prefix = "env/dev"
    }
}