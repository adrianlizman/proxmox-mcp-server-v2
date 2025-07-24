#!/bin/bash

# Proxmox MCP Server - Performance Testing Script
# Tests server performance and response times

set -e

# Configuration
SERVER_URL="http://172.32.0.200:8000"  # Change for Docker: http://localhost:8000
CONCURRENT_REQUESTS=10
TEST_DURATION=60
RESULTS_DIR="performance_results_$(date +%Y%m%d_%H%M%S)"

echo "========================================"
echo "  Proxmox MCP Server - Performance Test"
echo "========================================"
echo "Server URL: $SERVER_URL"
echo "Concurrent requests: $CONCURRENT_REQUESTS"
echo "Test duration: $TEST_DURATION seconds"
echo "Results directory: $RESULTS_DIR"
echo ""

# Check if ab (Apache Bench) is installed
if ! command -v ab &> /dev/null; then
    echo "Error: Apache Bench (ab) is not installed."
    echo "Install with: sudo apt-get install apache2-utils"
    exit 1
fi

# Create results directory
mkdir -p $RESULTS_DIR

echo "Starting performance tests..."

# Function to run performance test
run_perf_test() {
    local endpoint=$1
    local description=$2
    local output_file="$RESULTS_DIR/${endpoint//\//_}.txt"

    echo "Testing: $description"
    echo "Running ab -n 100 -c $CONCURRENT_REQUESTS $SERVER_URL$endpoint"

    ab -n 100 -c $CONCURRENT_REQUESTS "$SERVER_URL$endpoint" > "$output_file" 2>&1

    # Extract key metrics
    echo "Results for $description:" >> "$RESULTS_DIR/summary.txt"
    grep "Requests per second:" "$output_file" >> "$RESULTS_DIR/summary.txt" || echo "  No RPS data" >> "$RESULTS_DIR/summary.txt"
    grep "Time per request:" "$output_file" | head -1 >> "$RESULTS_DIR/summary.txt" || echo "  No timing data" >> "$RESULTS_DIR/summary.txt"
    grep "Failed requests:" "$output_file" >> "$RESULTS_DIR/summary.txt" || echo "  No failure data" >> "$RESULTS_DIR/summary.txt"
    echo "" >> "$RESULTS_DIR/summary.txt"

    echo "  Results saved to: $output_file"
    echo ""
}

# Initialize summary file
echo "Performance Test Summary - $(date)" > "$RESULTS_DIR/summary.txt"
echo "Server URL: $SERVER_URL" >> "$RESULTS_DIR/summary.txt"
echo "Concurrent requests: $CONCURRENT_REQUESTS" >> "$RESULTS_DIR/summary.txt"
echo "========================================" >> "$RESULTS_DIR/summary.txt"
echo "" >> "$RESULTS_DIR/summary.txt"

# Run performance tests
run_perf_test "/" "Root endpoint"
run_perf_test "/health" "Health check"
run_perf_test "/proxmox/nodes" "Proxmox nodes"
run_perf_test "/ollama/models" "Ollama models"

echo "========================================"
echo "Performance testing completed!"
echo ""
echo "Results summary:"
cat "$RESULTS_DIR/summary.txt"
echo ""
echo "Detailed results available in: $RESULTS_DIR/"
