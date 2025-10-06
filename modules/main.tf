// where source code will be stored
resource "google_storage_bucket" "default" {
    name = "${var.project}-gcf-source"
    location = "europe-west10"
    uniform_bucket_level_access = true
    force_destroy = true
}

// storing the bucket with json data coming from different Cloud Functions
resource "google_storage_bucket" "apis" {
    name = "${var.project}-apis"
    location = "europe-west10"
    uniform_bucket_level_access = true
    force_destroy = true

    cors {
      origin          = ["https://anselboero.com"]
      method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
      response_header = ["*"]
  }
}

// Storing here all the custom images used within the blog
resource "google_storage_bucket" "images" {
    name = "${var.project}-images"
    location = "europe-west10"
    uniform_bucket_level_access = true
    force_destroy = true

    cors {
      origin          = ["https://anselboero.com"]
      method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
      response_header = ["*"]
  }
}

// public read-only access to the bucket
data "google_iam_policy" "viewer" {
  binding {
    role = "roles/storage.objectViewer"
    members = [
        "allUsers",
    ] 
  }
}

// adding public access to buckets
resource "google_storage_bucket_iam_policy" "editor_apis" {
  bucket = "${google_storage_bucket.apis.name}"
  policy_data = "${data.google_iam_policy.viewer.policy_data}"
}

resource "google_storage_bucket_iam_policy" "editor_images" {
  bucket = "${google_storage_bucket.images.name}"
  policy_data = "${data.google_iam_policy.viewer.policy_data}"
}

data "archive_file" "gsheet-to-gcs" {
    type = "zip"
    output_path = "/tmp/function-source-gsheet-to-gcs.zip"
    // TODO: Find alternative to this path, don't like it
    source_dir = "../../modules/cloud_run_functions/functions/gsheet_to_gcs/"
}

data "archive_file" "update-running-images" {
    type = "zip"
    output_path = "/tmp/function-source-update-running-images.zip"
    // TODO: Find alternative to this path, don't like it
    source_dir = "../../modules/cloud_run_functions/functions/update_running_images/"
}

// name of the file in the bucket. Should change every time the source code changes,
// in order to enable Terraform trigger the cloud run rebuild
// the output_sha changes every time the source code is updated.
// source: https://stackoverflow.com/questions/68488277/how-can-i-deploy-google-cloud-functions-in-ci-cd-without-re-deploying-unchanged/68488770#68488770
locals {
  gsheet_to_gcs_zip_archive_name = "gsheet_to_gcs_source_code_${data.archive_file.gsheet-to-gcs.output_sha}.zip"
}

locals {
  update_running_images_zip_archive_name = "update_running_images_source_code_${data.archive_file.update-running-images.output_sha}.zip"
}

resource "google_storage_bucket_object" "gsheet_to_gcs_sc" {
    name   = local.gsheet_to_gcs_zip_archive_name
    bucket = google_storage_bucket.default.name
    source = data.archive_file.gsheet-to-gcs.output_path # Add path to the zipped function source code
}

resource "google_storage_bucket_object" "update_running_images_sc" {
    name   = local.update_running_images_zip_archive_name
    bucket = google_storage_bucket.default.name
    source = data.archive_file.update-running-images.output_path # Add path to the zipped function source code
}

// name should not have underscores (_)
resource "google_cloudfunctions2_function" "gsheet-to-gcs" {
    name        = "gsheet-to-gcs"
    location    = "europe-west10"
    description = "Given a Spreadsheet containing an API sheet, will store the result to JSON file"

    build_config {
      runtime     = "python312"
      entry_point = "gsheet_to_gcs" # Set the entry point
      source {
        storage_source {
          bucket = google_storage_bucket.default.name
          object = google_storage_bucket_object.gsheet_to_gcs_sc.name
        }
      }
    }

    depends_on = [google_storage_bucket.apis]

    service_config {
      max_instance_count = 1
      available_memory   = "256M"
      timeout_seconds    = 60
    }
}

// running images
resource "google_cloudfunctions2_function" "update-running-images" {
    name        = "update-running-images"
    location    = "europe-west10"
    description = "Given a csv containing running date, will store the graph as png to a GCS bucket"

    build_config {
      runtime     = "python312"
      entry_point = "update_running_images" # Set the entry point
      source {
        storage_source {
          bucket = google_storage_bucket.default.name
          object = google_storage_bucket_object.update_running_images_sc.name
        }
      }
    }

    depends_on = [google_storage_bucket.images]

    service_config {
      max_instance_count = 1
      available_memory   = "512M"
      timeout_seconds    = 60
    }
}

// triggering the function every 6 hours
resource "google_cloud_scheduler_job" "get-last-movie-watched" {
  name        = "trigger-get-last-movie-watched"
  description = "Trigger the Cloud Function every 6 hours"
  region = "europe-west3"

  schedule    = "0 */6 * * *" # Every 6 hours
  time_zone   = "UTC"         # Specify your desired time zone

  http_target {
    http_method = "POST"  # Use GET or POST depending on your function
    uri         = google_cloudfunctions2_function.gsheet-to-gcs.service_config[0].uri
    body        = base64encode(jsonencode({
      spreadsheet_id = "1evnjLFzM3apXph0sUahqcbCwuEKCeAZh6bp3bdshSm4"
      gcs_bucket_name    = google_storage_bucket.apis.name
      json_output_filename  = "last_movie_watched.json"
    }))

    headers = {
      "Content-Type" = "application/json"
    }

    oidc_token {
      service_account_email = var.service_account_email
    }
  }
  # Set a deadline for the job's execution
  attempt_deadline = "320s" # Maximum execution time of 320 seconds
}

resource "google_cloud_scheduler_job" "get-currently-reading-book" {
  name        = "trigger-get-currently-reading-book"
  description = "Trigger the Cloud Function every 6 hours. Triggering the currently reading book."
  region = "europe-west3"

  schedule    = "0 */6 * * *" # Every 6 hours
  time_zone   = "UTC"         # Specify your desired time zone

  http_target {
    http_method = "POST"  # Use GET or POST depending on your function
    uri         = google_cloudfunctions2_function.gsheet-to-gcs.service_config[0].uri
    body        = base64encode(jsonencode({
      spreadsheet_id = "14vh5NBXbr2XAVyDW-EyhlpVUKcfPGtkiHh85gDdVz5o"
      gcs_bucket_name    = google_storage_bucket.apis.name
      json_output_filename  = "currently_reading_book.json"
    }))

    headers = {
      "Content-Type" = "application/json"
    }

    oidc_token {
      service_account_email = var.service_account_email
    }
  }
  # Set a deadline for the job's execution
  attempt_deadline = "320s" # Maximum execution time of 320 seconds
}

resource "google_cloud_scheduler_job" "update_running_images" {
  name        = "trigger-update-running-images"
  description = "Trigger the Cloud Function every 24 hours. Triggering the currently reading book."
  region = "europe-west3"

  schedule    = "0 0 * * *" # Every 6 hours
  time_zone   = "UTC"         # Specify your desired time zone

  http_target {
    http_method = "POST"  # Use GET or POST depending on your function
    uri         = google_cloudfunctions2_function.update-running-images.service_config[0].uri
    body        = base64encode(jsonencode({
      SOURCE_BUCKET    = google_storage_bucket.images.name
      DESTINATION_BUCKET  = google_storage_bucket.images.name
    }))

    headers = {
      "Content-Type" = "application/json"
    }

    oidc_token {
      service_account_email = var.service_account_email
    }
  }
  # Set a deadline for the job's execution
  attempt_deadline = "320s" # Maximum execution time of 320 seconds
}

resource "google_cloud_scheduler_job" "get-net-worth" {
  name        = "trigger-get-net-worth"
  description = "Trigger the Cloud Function every 6 hours"
  region = "europe-west3"

  schedule    = "0 */6 * * *" # Every 6 hours
  time_zone   = "UTC"         # Specify your desired time zone

  http_target {
    http_method = "POST"  # Use GET or POST depending on your function
    uri         = google_cloudfunctions2_function.gsheet-to-gcs.service_config[0].uri
    body        = base64encode(jsonencode({
      spreadsheet_id = "1G_CqV95lI7r-XtgpO5UOzsB_h77G4JVV9kThdzfsujk"
      gcs_bucket_name    = google_storage_bucket.apis.name
      json_output_filename  = "net_worth.json"
    }))
    headers = {
      "Content-Type" = "application/json"
    }

    oidc_token {
      service_account_email = var.service_account_email
    }
  }
  # Set a deadline for the job's execution
  attempt_deadline = "320s" # Maximum execution time of 320 seconds
}