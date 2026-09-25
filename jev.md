

curl 'https://jevplayground.com/api/evaluate' \
  -H 'accept: */*' \
  -H 'accept-language: en-US,en;q=0.9,ar-AE;q=0.8,ar;q=0.7' \
  -H 'content-type: application/json' \
  -H 'origin: https://jevplayground.com' \
  -H 'priority: u=1, i' \
  -H 'referer: https://jevplayground.com/' \
  -H 'sec-ch-ua: "Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Linux"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-origin' \
  -H 'user-agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36' \
  --data-raw '{"state":"The user send a query \"open terminal in remotion folder\", a tool was called and the output was \"success, opened remotion folder in the terminal\n\"","questions":{"decision":{"instructions":"What should the agent do next?","type":"choice","criteria":{"Retry":"Retry","Continue":"Continue","Reply to the user":"Reply to the user","Use Tool":"Use Tool"}}}}' | jq .

{
  "ok": true,
  "model": "typesafe-ai/jev",
  "latencyMs": 111.1,
  "result": {
    "answers": {
      "decision": {
        "type": "choice",
        "choice": "Reply to the user",
        "probabilities": {
          "Retry": 0,
          "Continue": 0.05,
          "Reply to the user": 0.95,
          "Use Tool": 0
        }
      }
    },
    "usage": {
      "inputTokens": 372,
      "outputTokens": 52,
      "totalTokens": 424
    },
    "confidence": {
      "decision": 0.93
    },
    "warnings": []
  }
}
