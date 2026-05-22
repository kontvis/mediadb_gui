curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet-latest",
    "max_tokens": 500,
    "messages": [
      {
        "role": "user",
        "content": "Extract the title, author, and publisher from this text: The Fellowship of the Ring by J.R.R. Tolkien, published by Allen & Unwin."
      }
    ]
  }'
