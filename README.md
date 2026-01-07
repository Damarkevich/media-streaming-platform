# media-streaming-platform
Production-ready microservices backend for an online cinema platform.

# Project Documentation

## 1. What is this

This project appears to be a software application that utilizes Docker containerization for deployment and orchestration. The project structure includes an `infra` folder which contains infrastructure-related configuration files, specifically Docker Compose setup for managing multi-container Docker applications.

## 2. How to run using docker-compose from infra folder

To run this project using Docker Compose from the `infra` folder:

1. Navigate to the `infra` directory:
    ```bash
    cd infra
    ```

2. Start the services using Docker Compose:
    ```bash
    docker-compose up
    ```

3. To run in detached mode (background):
    ```bash
    docker-compose up -d
    ```

4. To stop the services:
    ```bash
    docker-compose down
    ```

**Prerequisites:**
- Docker must be installed on your system
- Docker Compose must be installed on your system