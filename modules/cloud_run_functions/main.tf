// where source code will be stored
resource "google_storage_bucket" "default" {
    name = "${var.project}-gcf-source"
    location = "europe-west10"
    uniform_bucket_level_access = true
}

data "archive_file" "default" {
    type = "zip"
    output_path = "/tmp/function-source.zip"
    // TODO: Find alternative to this path, don't like it
    source_dir = "../../modules/cloud_run_functions/functions/get_last_movie_watched/"
}

resource "google_storage_bucket_object" "object" {
    name   = "function-source.zip"
    bucket = google_storage_bucket.default.name
    source = data.archive_file.default.output_path # Add path to the zipped function source code
}

// name should not have underscores (_)
resource "google_cloudfunctions2_function" "default" {
    name        = "get-last-movie-watched"
    location    = "europe-west10"
    description = "Get Last movie watched from MyMoviesDb Gsheet"

    build_config {
      runtime     = "python312"
      entry_point = "get_last_movie_watched" # Set the entry point
      source {
        storage_source {
          bucket = google_storage_bucket.default.name
          object = google_storage_bucket_object.object.name
        }
      }
    }

    service_config {
      max_instance_count = 1
      available_memory   = "256M"
      timeout_seconds    = 60
    }
  }

// assign public access to the Function
resource "google_cloud_run_service_iam_member" "member" {
  location = google_cloudfunctions2_function.default.location
  service  = google_cloudfunctions2_function.default.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "function_uri" {
    value = google_cloudfunctions2_function.default.service_config[0].uri
}