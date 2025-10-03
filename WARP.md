# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Architecture

This project implements a secure, containerized version of the `whisper-asr-webservice`. It uses FastAPI for the web framework, Redis for authentication and pub/sub, and Docker for containerization.

The application is structured as follows:

-   `app/`: Main application code.
    -   `asr_models/`: Whisper ASR model management.
    -   `health/`: Health check endpoints.
    -   `middleware/`: Authentication and other middleware.
    -   `monitoring/`: Monitoring and analytics.
    -   `utils/`: Utility functions.
    -   `websocket/`: WebSocket handling.
-   `certs/`: TLS certificates.
-   `config/`: Application configuration.
-   `logs/`: Application logs.
-   `monitoring/`: Monitoring services configuration.
-   `tests/`: Tests (currently empty).
-   `Dockerfile`: Defines the Docker image for the application.
-   `docker-compose.yml`: Defines the services, networks, and volumes for the application.

## Common Commands

### Building and Running

-   **Build and run the application in production mode:**
    ```bash
    docker-compose up --build -d
    ```
-   **Run in development mode (with a local Redis container):**
    ```bash
    docker-compose --profile dev up --build -d
    ```
-   **Run with monitoring (Redis Insight):**
    ```bash
    docker-compose --profile monitoring up --build -d
    ```
-   **Stop the application:**
    ```bash
    docker-compose down
    ```

### Testing

The `tests` directory is currently empty. To run tests, you will likely need to execute them within the Docker container.

-   **Run tests (once they are created):**
    ```bash
    docker-compose exec whisper-asr-secure poetry run pytest
    ```

### Linting

-   **Lint the code:**
    ```bash
    docker-compose exec whisper-asr-secure poetry run ruff check .
    ```

-   **Format the code:**
    ```bash
    docker-compose exec whisper-asr-secure poetry run ruff format .
    ```

## Development Notes

-   The application is configured to use TLS, so it will be available at `https://localhost:9443`.
-   Authentication is handled via bearer tokens stored in Redis.
-   The project is set up to use Upstash Redis, but for local development, a Redis container is provided in the `docker-compose.yml` file. You will need to set the `REDIS_URL` and `REDIS_PASSWORD` environment variables to connect to your Upstash instance.
