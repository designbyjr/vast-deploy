#!/bin/bash

# Secure Whisper ASR Service - Docker Management Script

set -e

CONTAINER_NAME="whisper-asr-secure"
IMAGE_NAME="whisper-asr-secure:latest"
HOST_PORT="9443"
CONTAINER_PORT="9443"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to build the Docker image
build() {
    log "Building Docker image: $IMAGE_NAME"
    docker build -t $IMAGE_NAME .
    log "✅ Build complete!"
}

# Function to run the container
run() {
    log "Checking if container $CONTAINER_NAME is already running..."
    
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        warn "Container $CONTAINER_NAME is already running"
        log "Stopping existing container..."
        docker stop $CONTAINER_NAME
        docker rm $CONTAINER_NAME
    fi
    
    log "Starting new container: $CONTAINER_NAME"
    
    # Create directories for volumes
    mkdir -p ./certs ./logs
    
    docker run -d \
        --name $CONTAINER_NAME \
        --restart unless-stopped \
        -p $HOST_PORT:$CONTAINER_PORT \
        -v $(pwd)/certs:/app/certs:rw \
        -v $(pwd)/logs:/app/logs:rw \
        --security-opt no-new-privileges:true \
        $IMAGE_NAME
    
    log "✅ Container started successfully!"
    log "🌐 Service available at: https://localhost:$HOST_PORT"
    log "📚 API Documentation: https://localhost:$HOST_PORT/docs"
    log "❤️  Health Check: https://localhost:$HOST_PORT/health"
    
    # Show container status
    docker ps -f name=$CONTAINER_NAME
}

# Function to stop the container
stop() {
    log "Stopping container: $CONTAINER_NAME"
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        docker stop $CONTAINER_NAME
        docker rm $CONTAINER_NAME
        log "✅ Container stopped and removed"
    else
        warn "Container $CONTAINER_NAME is not running"
    fi
}

# Function to show logs
logs() {
    log "Showing logs for container: $CONTAINER_NAME"
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        docker logs -f $CONTAINER_NAME
    else
        error "Container $CONTAINER_NAME is not running"
    fi
}

# Function to show container status
status() {
    log "Container status:"
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        docker ps -f name=$CONTAINER_NAME
        echo
        log "Container health:"
        docker inspect --format='{{.State.Health.Status}}' $CONTAINER_NAME 2>/dev/null || echo "Health status not available"
        echo
        log "Recent container logs:"
        docker logs --tail 10 $CONTAINER_NAME
    else
        warn "Container $CONTAINER_NAME is not running"
    fi
}

# Function to enter the container
shell() {
    log "Opening shell in container: $CONTAINER_NAME"
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        docker exec -it $CONTAINER_NAME /bin/bash
    else
        error "Container $CONTAINER_NAME is not running"
    fi
}

# Function to clean up Docker resources
clean() {
    log "Cleaning up Docker resources..."
    
    # Stop and remove container
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        docker stop $CONTAINER_NAME
        docker rm $CONTAINER_NAME
    fi
    
    # Remove image
    if docker images -q $IMAGE_NAME | grep -q .; then
        docker rmi $IMAGE_NAME
    fi
    
    log "✅ Cleanup complete"
}

# Function to rebuild and run
restart() {
    log "Rebuilding and restarting container..."
    stop
    build
    run
}

# Help function
help() {
    echo "Secure Whisper ASR Service - Docker Management"
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  build     Build the Docker image"
    echo "  run       Run the container (builds if needed)"
    echo "  stop      Stop and remove the container"
    echo "  restart   Stop, rebuild, and run the container"
    echo "  logs      Show container logs (follow)"
    echo "  status    Show container status and health"
    echo "  shell     Open a shell inside the container"
    echo "  clean     Remove container and image"
    echo "  help      Show this help message"
    echo
    echo "Examples:"
    echo "  $0 run      # Build and run the service"
    echo "  $0 logs     # Follow the logs"
    echo "  $0 status   # Check service status"
}

# Main command handling
case "${1:-help}" in
    build)
        build
        ;;
    run)
        # Build if image doesn't exist
        if ! docker images -q $IMAGE_NAME | grep -q .; then
            build
        fi
        run
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs
        ;;
    status)
        status
        ;;
    shell)
        shell
        ;;
    clean)
        clean
        ;;
    help|--help|-h)
        help
        ;;
    *)
        error "Unknown command: $1"
        help
        exit 1
        ;;
esac