import json
import anthropic

def analyze_reviews(reviews: list[dict], client: anthropic.Anthropic) -> dict:
    """
    Send reviews to Claude for analysis. Returns dict with:
    - sentiment: {positive: %, neutral: %, negative: %}
    - themes: list of {theme, count, examples}
    - summary: str
    - action_items: list of str
    """
    if not reviews:
        return {}

    # Prepare a compact representation
    review_text = "\n".join(
        f"[{r['date']} | {r['rating']}★] {r['text'][:300]}"
        for r in reviews[:500]  # cap to 500 for prompt length
    )

    prompt = f"""You are a product analyst reviewing user feedback for a fintech app (INDMoney).

Here are {len(reviews)} app reviews (showing up to 500):

{review_text}

Analyze these reviews and respond with ONLY valid JSON in this exact structure:
{{
  "sentiment": {{
    "positive": <integer 0-100>,
    "neutral": <integer 0-100>,
    "negative": <integer 0-100>
  }},
  "themes": [
    {{
      "theme": "<theme name>",
      "count": <approximate number of reviews mentioning this>,
      "sentiment": "positive|neutral|negative",
      "examples": ["<short quote 1>", "<short quote 2>"]
    }}
  ],
  "summary": "<2-3 sentence summary for the product team>",
  "action_items": [
    "<specific actionable recommendation>",
    ...
  ]
}}

Return top 5 themes. Sentiment percentages must add up to 100."""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)
