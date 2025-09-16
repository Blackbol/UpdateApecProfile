# APEC Profile Updater

A Java-based project to automate the process of updating a profile on the APEC website. This project uses Selenium WebDriver for browser automation.

---

## Features

- Automatically logs in to the APEC website.
- Updates the job profile.
- Handles cookie consent banners.
- Runs in headless mode to avoid displaying the browser GUI.
- Dockerized for easy deployment and scheduling.

---

## Prerequisites

- Java Development Kit (JDK) 1.8 or later (for local development)
- Maven (for local development)
- Docker
- Docker Compose

---

## Docker Setup

This project is fully Dockerized and can be run using Docker Compose. The setup includes:

- A Selenium container for browser automation.
- An application container for running the APEC Profile Updater.
- A scheduler container for managing the execution schedule.

### Docker Compose Configuration

```yaml
version: '3.8'

services:
  # Selenium service: Runs a standalone Chrome instance for Selenium
  selenium:
    image: selenium/standalone-chrome\:latest
    container_name: selenium_standalone
    ports:
      - "4444:4444"  # Port for Selenium WebDriver
      - "7900:7900"  # Port for VNC access (optional)
    shm_size: 2g     # Shared memory size for Chrome
    networks:
      - app-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4444/wd/hub/status"]
      interval: 10s
      timeout: 5s
      retries: 5

  # UpdateApecProfile service: Runs the application to update the APEC profile
  updateapecprofile:
    image: ghcr.io/blackbol/update-apec-profile\:latest
    container_name: UpdateApecProfile
    depends_on:
      selenium:
        condition: service_healthy  # Wait for Selenium to be healthy
    environment:
      - SELENIUM_HUB_URL=http://selenium:4444/wd/hub
      # Add your credentials via environment variables or a .env file
      - APEC_USERNAME=apec_username
      - APEC_PASSWORD=apec_password
    networks:
      - app-network

  # Scheduler service: Uses Ofelia to schedule the execution of the services
  scheduler:
    image: ghcr.io/blackbol/ofelia_docker\:latest
    container_name: scheduler
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock\:ro  # Access to Docker socket
    command: daemon --docker
    labels:
      # Start selenium at 08:50 AM
      ofelia.job-run.start_selenium.schedule: "50 8 * * *"
      ofelia.job-run.start_selenium.command: "docker start selenium_standalone"

      # Start updateapecprofile at 08:55 AM and monitor its execution
      ofelia.job-run.start_updateapecprofile.schedule: "55 8 * * *"
      ofelia.job-run.start_updateapecprofile.command: >
        sh -c 'docker start UpdateApecProfile &&
        while docker inspect -f "{{.State.Running}}" UpdateApecProfile | grep -q "true"; do
          sleep 10;
        done;
        docker stop selenium_standalone'
    restart: always  # Ensures the scheduler is always running

networks:
  app-network:
    driver: bridge
