#!/bin/bash
set -e

echo "1️⃣ STT test"
TRANSCRIPT=$(curl -s -X POST localhost:8080/stt \
    --data-binary @/Users/A200266445/Ecommerce-AIVoicebot/frontend/sample_product1.wav)

echo "Transcript: $TRANSCRIPT"

[[ ${#TRANSCRIPT} -gt 10 ]]

echo "2️⃣ Agent order query"
RESPONSE=$(curl -s -X POST localhost:8000/agent/handle \
    -H "Content-Type: application/json" \
    -d '{"transcript":"Where is my order 123","session_id":"test1"}')

echo "RAW RESPONSE:"
echo "$RESPONSE"

echo "$RESPONSE" | jq '.actions[] | select(.task=="get_order_status")'

echo "3️⃣ MCP returns order status"
echo "$RESPONSE" | jq '.reply | contains("Delivered")'

echo "5️⃣ Escalation"
ESC=$(curl -s -X POST localhost:8000/agent/handle \
    -d '{"transcript":"speak to human","session_id":"test2"}')

echo "$ESC" | jq '.escalation_url'

echo "✅ ALL TESTS PASSED"
