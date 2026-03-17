#!/bin/bash
#
# MCP Services Validation Script
# Checks service health and security configurations
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Service configuration
SERVICES=(
    "searxng:18880:/health"
    "easyocr:18881:/health"
    "playwright:18882:/health"
    "firecrawl:18883:/health"
)

echo "=============================================="
echo "  Local MCP Services Validation"
echo "=============================================="
echo ""

# Track overall status
OVERALL_STATUS=0

# Function to check service health
check_service() {
    local name=$1
    local port=$2
    local endpoint=$3

    echo -n "Checking $name... "

    if curl -sf "http://localhost:$port$endpoint" > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        OVERALL_STATUS=1
        return 1
    fi
}

# Function to check security configuration
check_security() {
    local container=$1

    echo -n "  Security: "

    # Check if running as non-root
    user=$(docker exec "$container" whoami 2>/dev/null || echo "unknown")
    if [ "$user" = "root" ]; then
        echo -e "${RED}Running as root!${NC}"
        OVERALL_STATUS=1
        return 1
    fi

    # Check read-only filesystem
    readonly=$(docker inspect "$container" --format '{{.HostConfig.ReadonlyRootfs}}' 2>/dev/null || echo "unknown")
    if [ "$readonly" != "true" ]; then
        echo -e "${YELLOW}Not read-only${NC}"
    fi

    # Check memory limit
    memory=$(docker inspect "$container" --format '{{.HostConfig.Memory}}' 2>/dev/null || echo "0")
    if [ "$memory" = "0" ]; then
        echo -e "${RED}No memory limit!${NC}"
        OVERALL_STATUS=1
        return 1
    fi

    echo -e "${GREEN}OK${NC} (user: $user)"
    return 0
}

echo "1. Service Health Checks"
echo "------------------------"

# Check all services
for service in "${SERVICES[@]}"; do
    IFS=':' read -r name port endpoint <<< "$service"
    check_service "$name" "$port" "$endpoint"
done

echo ""
echo "2. Security Configuration"
echo "------------------------"

# Check each container
for service in "${SERVICES[@]}"; do
    IFS=':' read -r name port endpoint <<< "$service"
    check_security "$name"
done

echo ""
echo "3. Network Isolation"
echo "--------------------"

# Check network isolation
for service in "${SERVICES[@]}"; do
    IFS=':' read -r name port endpoint <<< "$service"

    echo -n "  $name on mcp-net... "

    network=$(docker inspect "$name" --format '{{range .NetworkSettings.Networks}}{{.NetworkID}}{{end}}' 2>/dev/null || echo "")

    if echo "$network" | grep -q "mcp"; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${YELLOW}Not on mcp-net${NC}"
    fi
done

echo ""
echo "4. Resource Limits"
echo "------------------"

# Check resource limits
for service in "${SERVICES[@]}"; do
    IFS=':' read -r name port endpoint <<< "$service"

    echo -n "  $name... "

    memory=$(docker inspect "$name" --format '{{.HostConfig.Memory}}' 2>/dev/null || echo "0")
    cpus=$(docker inspect "$name" --format '{{.HostConfig.NanoCpus}}' 2>/dev/null || echo "0")

    if [ "$memory" != "0" ] && [ "$cpus" != "0" ]; then
        memory_mb=$((memory / 1024 / 1024))
        cpus_int=$((cpus / 100000000))
        echo -e "${GREEN}OK${NC} (${memory_mb}MB, ${cpus_int} CPUs)"
    else
        echo -e "${RED}No limits${NC}"
        OVERALL_STATUS=1
    fi
done

echo ""
echo "=============================================="

if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "Status: ${GREEN}ALL CHECKS PASSED${NC}"
    exit 0
else
    echo -e "Status: ${RED}SOME CHECKS FAILED${NC}"
    exit 1
fi
