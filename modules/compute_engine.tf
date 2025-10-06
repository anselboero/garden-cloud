# compute.tf

# 1. The Compute Engine VM Instance
# Falling on the Free Tier
resource "google_compute_instance" "free_tier_vm" {
  name         = "free-tier-instance"
  machine_type = "e2-micro"
  zone         = "us-east1-b"

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 12
      type  = "pd-standard"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  tags = ["ssh-access"]
}

# 2. A Firewall Rule to Allow SSH Access
resource "google_compute_firewall" "allow_ssh" {
  name    = "allow-ssh-for-free-vm"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  target_tags   = ["ssh-access"]
  source_ranges = ["0.0.0.0/0"]
}