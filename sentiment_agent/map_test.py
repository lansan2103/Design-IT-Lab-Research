import requests
import os
from dotenv import load_dotenv
import math
from transformers import pipeline

load_dotenv()
api_key = os.getenv("GOOGLE_MAPS_API_KEY") or "YOUR_API_KEY_HERE"

sentiment_analyzer = pipeline(
    "sentiment-analysis",
    model="distilbert/distilbert-base-uncased-finetuned-sst-2-english",
    revision="714eb0f"
)

def get_place_id_and_location(query, api_key):
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.id,places.location,places.displayName"
    }
    data = {"textQuery": query}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        places = response.json().get("places", [])
        if places:
            place = places[0]
            return place["id"], place["location"], place["displayName"]["text"]
    else:
        print("Search Error:", response.text)
    return None, None, None

def get_place_details(place_id, api_key):
    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "reviews.text,reviews.rating"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("reviews", [])
    else:
        print("Details Error:", response.text)
        return []

def get_nearby_places(location, api_key, radius=1000):
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.id,places.location,places.displayName,places.rating,places.userRatingCount"
    }
    data = {
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
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json().get("places", [])
    else:
        print("Nearby Search Error:", response.text)
        return []

def analyze_reviews_sentiment(reviews):
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

# === MAIN ===
query = input("Enter a place to search: ")
place_id, location, name = get_place_id_and_location(query, api_key)

if place_id:
    print(f"\n✅ Nearby places around: {name}")
    places = get_nearby_places(location, api_key)

    ranked = []
    for p in places:
        pid = p["id"]
        pname = p["displayName"]["text"]
        rating = p.get("rating", 0)
        review_count = p.get("userRatingCount", 0)

        # Popularity score approximation
        popularity_score = rating * math.log(review_count + 1)

        # Optional: analyze sentiment
        reviews = get_place_details(pid, api_key)
        sentiment = analyze_reviews_sentiment(reviews)

        ranked.append({
            "name": pname,
            "rating": rating,
            "reviews": review_count,
            "popularity": popularity_score,
            "sentiment": sentiment
        })

    # Sort by popularity score descending
    ranked_sorted = sorted(ranked, key=lambda x: x["popularity"], reverse=True)

    # Print results
    for i, place in enumerate(ranked_sorted, 1):
        print(f"\n{i}. {place['name']}")
        print(f"   Avg Rating: {place['rating']:.1f} ({place['reviews']} reviews)")
        print(f"   Popularity Score: {place['popularity']:.2f}")
        print(f"   Avg Sentiment Score: {place['sentiment']:.2f}")
else:
    print("Place not found.")
