#!/bin/bash

API_URL="http://localhost:8000/agent/handle"

run_test() {
  echo "=============================="
  echo "Test: $1"
  echo "Input: $2"
  curl -s -X POST $API_URL \
    -H "Content-Type: application/json" \
    -d "{
      \"transcript\": \"$2\",
      \"session_id\": \"demo-session-1\"
    }" | jq .
}

run_test "Product Search" "Show red cotton size size M"
run_test "FAQ" "How long does delivery take?"
run_test "Policy" "What is your return policy?"
run_test "Order Tracking" "Where is my order ORD-1002?"
run_test "Escalation" "I want to talk to a human"
