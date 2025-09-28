import os
import math
import requests
from dotenv import load_dotenv
from typing import Optional, List
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END
import google.generativeai as genai
from transformers import pipeline
from flask import Flask, request, jsonify
from langchain_core.tools import tool
import re

load_dotenv()
api_key = os.getenv("GOOGLE_MAPS_API_KEY")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")
sentiment_analyzer = pipeline("sentiment-analysis")

class State(TypedDict):
    user_input: str
    search_query: str
    location: Optional[dict]
    display_name: Optional[str]
    places: List[dict]
    avg_rating: Optional[float]
    avg_review_count: Optional[int]
    avg_popularity: Optional[float]
    avg_sentiment_score: Optional[float]
    summaries: Optional[str]
    compare_inputs: Optional[List[str]]  # List of neighborhoods to compare
    comparison: Optional[str]  # Comparison summary

def interpret_query(state: State) -> dict:
    user_input = state["user_input"]
    # Detect comparison queries (e.g., 'A vs B', 'A versus B', 'A and B', 'A, B')
    compare_match = re.split(r"\s+vs\.?\s+|\s+versus\s+|\s+and\s+|,\s*", user_input, flags=re.IGNORECASE)
    compare_names = [s.strip() for s in compare_match if s.strip()]
    if len(compare_names) >= 2:
        # This is a comparison query, trigger the tool
        return {"compare_inputs": compare_names}
    # Otherwise, normal single neighborhood
    prompt = f"""
You are a travel assistant. The user asked: "{user_input}". 
Turn this into a Google Maps search query for the Places API focusing on a neighborhood or district.
Only return the query string.
"""
    response = model.generate_content(prompt)
    query = response.text.strip().strip('"')
    print("🔍 Interpreted Query:", query)
    return {"search_query": query}

def get_place_info(state: State) -> dict:
    query = state["search_query"]
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.location,places.displayName"
    }
    data = {"textQuery": query}
    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        print("❌ Place Search Error:", response.text)
        return {}

    places = response.json().get("places", [])
    if not places:
        return {}

    place = places[0]
    print("📍 Found Neighborhood:", place["displayName"]["text"])
    return {
        "location": place["location"],
        "display_name": place["displayName"]["text"]
    }

import time

def get_nearby_places(location, radius=1500) -> List[dict]:
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.id,places.location,places.displayName,places.rating,places.userRatingCount"
        )
    }

    all_places = []
    next_page_token = None

    while True:
        payload = {
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": location["latitude"],
                        "longitude": location["longitude"]
                    },
                    "radius": radius
                }
            }
        }

        if next_page_token:
            payload["pageToken"] = next_page_token
            print("⏳ Waiting for next page...")
            time.sleep(2)  # Google requires this delay before using nextPageToken

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            print("❌ Nearby Search Error:", response.text)
            break

        data = response.json()
        places = data.get("places", [])
        all_places.extend(places)

        print(f"✅ Fetched {len(places)} places, total so far: {len(all_places)}")

        next_page_token = data.get("nextPageToken")
        if not next_page_token:
            break

    return all_places

def analyze_sentiment(reviews):
    scores = []
    for review in reviews:
        text = review.get("text", {}).get("text", "")
        if text:
            result = sentiment_analyzer(text[:512])[0]
            score = result["score"] if result["label"] == "POSITIVE" else -result["score"]
            scores.append(score)
    if scores:
        return sum(scores) / len(scores)
    return 0.0

def get_reviews(place_id):
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "reviews.text"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("reviews", [])
    else:
        print("Review Fetch Error:", response.text)
        return []

def summarize_neighborhood(state: State) -> dict:
    location = state.get("location")
    display_name = state.get("display_name", "this neighborhood")

    places = get_nearby_places(location)
    if not places:
        return {"summaries": "No places found nearby to summarize.", "places": []}

    ratings = []
    review_counts = []
    popularity_scores = []
    sentiments = []
    sample_names = []
    places_with_sentiment = []

    for p in places[:1000]:  # limit to 1000 for performance
        rating = p.get("rating", 0)
        count = p.get("userRatingCount", 0)
        popularity = rating * math.log(count + 1) if rating and count else 0
        sample_names.append(p["displayName"]["text"])

        reviews = get_reviews(p["id"])
        sentiment = analyze_sentiment(reviews)

        ratings.append(rating)
        review_counts.append(count)
        popularity_scores.append(popularity)
        sentiments.append(sentiment)

        # Add to places_with_sentiment for frontend heatmap
        if "location" in p and "latitude" in p["location"] and "longitude" in p["location"]:
            places_with_sentiment.append({
                "location": {
                    "latitude": p["location"]["latitude"],
                    "longitude": p["location"]["longitude"]
                },
                "displayName": p["displayName"]["text"],
                "sentiment_score": sentiment
            })

    avg_rating = sum(ratings) / len(ratings)
    avg_review_count = sum(review_counts) / len(review_counts)
    avg_popularity = sum(popularity_scores) / len(popularity_scores)
    avg_sentiment = sum(sentiments) / len(sentiments)

    places_sample_str = ", ".join(sample_names)

    prompt = f"""
You are a cultural analyst. Describe the overall *sense of place* for the neighborhood "{display_name}".
Use the average ratings ({avg_rating:.1f}), review counts ({int(avg_review_count)}), popularity score ({avg_popularity:.2f}), and sentiment ({avg_sentiment:.2f}) to inform your description.
Mention the general atmosphere and feeling across places such as: {places_sample_str}.

Write a natural, engaging, but concise and short paragraph that captures the vibe and character of the neighborhood. Also include a list three one-word keywords at the bottom that encapsulate the areas unique sense of place.
"""
    response = model.generate_content(prompt)
    summary = response.text.strip()

    return {
        "avg_rating": avg_rating,
        "avg_review_count": int(avg_review_count),
        "avg_popularity": avg_popularity,
        "avg_sentiment_score": avg_sentiment,
        "summaries": summary,
        "places": places_with_sentiment,
        "place_count": len(places_with_sentiment)
    }

# === Graph ===
graph = StateGraph(State)
graph.add_node("interpret", interpret_query)
graph.add_node("lookup", get_place_info)
graph.add_node("summarize", summarize_neighborhood)

graph.set_entry_point("interpret")
graph.add_edge("interpret", "lookup")
graph.add_edge("lookup", "summarize")
graph.add_edge("summarize", END)

compiled_graph = graph.compile()

app = Flask(__name__)

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    user_input = data.get("user_input", "")
    result = compiled_graph.invoke({"user_input": user_input})
    print("🚀 Returned to frontend:", result)
    return jsonify(result)

@app.route("/")
def home():
    return app.send_static_file("frontend.html")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        app.run(host="0.0.0.0", port=5000, debug=True)
    else:
        user_input = input("Enter a neighborhood or district to learn about its vibe:\n> ")
        result = compiled_graph.invoke({"user_input": user_input})
        ...
