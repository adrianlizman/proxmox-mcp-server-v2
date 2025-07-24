#!/bin/bash

# Proxmox MCP Server - API Testing Script
# Tests all available API endpoints

set -e

# Configuration
SERVER_URL="http://172.32.0.200:8000"  # Change for Docker: http://localhost:8000
TEST_RESULTS_FILE="test_results_$(date +%Y%m%d_%H%M%S).log"

echo "========================================"
echo "  Proxmox MCP Server - API Testing"
echo "========================================"
echo "Server URL: $SERVER_URL"
echo "Results will be saved to: $TEST_RESULTS_FILE"
echo ""

# Function to test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local expected_code=${4:-200}
    local data=$5

    echo -n "Testing: $description... "

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" "$SERVER_URL$endpoint")
    elif [ "$method" = "POST" ]; then
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$SERVER_URL$endpoint")
    fi

    http_code=$(echo $response | tr -d '
' | sed -e 's/.*HTTPSTATUS://')
    body=$(echo $response | sed -e 's/HTTPSTATUS\:.*//g')

    if [ "$http_code" -eq "$expected_code" ]; then
        echo "PASS (HTTP $http_code)"
        echo "$(date): PASS - $description - HTTP $http_code" >> $TEST_RESULTS_FILE
        echo "Response: $body" >> $TEST_RESULTS_FILE
        echo "" >> $TEST_RESULTS_FILE
    else
        echo "FAIL (HTTP $http_code, expected $expected_code)"
        echo "$(date): FAIL - $description - HTTP $http_code (expected $expected_code)" >> $TEST_RESULTS_FILE
        echo "Response: $body" >> $TEST_RESULTS_FILE
        echo "" >> $TEST_RESULTS_FILE
    fi
}

# Initialize results file
echo "API Test Results - $(date)" > $TEST_RESULTS_FILE
echo "Server URL: $SERVER_URL" >> $TEST_RESULTS_FILE
echo "==========================================" >> $TEST_RESULTS_FILE
echo "" >> $TEST_RESULTS_FILE

echo "Starting API tests..."
echo ""

# Basic endpoint tests
test_endpoint "GET" "/" "Root endpoint"
test_endpoint "GET" "/health" "Health check endpoint"

# Proxmox API tests
test_endpoint "GET" "/proxmox/nodes" "Get Proxmox nodes"

# Note: The following tests may fail if specific nodes don't exist
# You may need to adjust node names based on your environment
echo ""
echo "Note: Node-specific tests may fail if nodes don't exist in your environment"

# Try to get VMs for common node names
for node in "proxmox" "pve" "node1"; do
    test_endpoint "GET" "/proxmox/node/$node/vms" "Get VMs for node $node" 200
done

# Ollama API tests
test_endpoint "GET" "/ollama/models" "Get Ollama models"

# Test AI generation (this may take longer)
echo ""
echo "Testing AI generation (may take 30+ seconds)..."
ai_request='{"model":"llama2","prompt":"Hello, respond with just: AI test successful","stream":false}'
test_endpoint "POST" "/ollama/generate" "Generate AI response" 200 "$ai_request"

echo ""
echo "========================================"
echo "API testing completed!"
echo "Results saved to: $TEST_RESULTS_FILE"
echo ""
echo "Summary:"
grep "PASS\|FAIL" $TEST_RESULTS_FILE | sort | uniq -c
echo ""
echo "View detailed results: cat $TEST_RESULTS_FILE"
