"""
Search tool for finding restaurants, hotels, events, and other information.
Integrates with external APIs like Google Places, Yelp, etc.
"""

from typing import Dict, List, Any, Optional
import requests
import os
from datetime import datetime


class SearchTool:
    """Tool for searching external APIs and services."""
    
    def __init__(self):
        self.google_places_key = os.getenv("GOOGLE_MAPS_API_KEY")
        self.yelp_key = os.getenv("YELP_API_KEY")
    
    async def search_restaurants(
        self,
        location: str,
        cuisine: Optional[str] = None,
        price_level: Optional[int] = None,
        radius: int = 5000,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for restaurants using Google Places API."""
        
        if not self.google_places_key:
            return self._mock_restaurant_data(location, cuisine)
        
        # Build search query
        query = "restaurants"
        if cuisine:
            query = f"{cuisine} restaurants"
        
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": f"{query} in {location}",
            "key": self.google_places_key,
            "type": "restaurant"
        }
        
        if price_level:
            params["maxprice"] = price_level
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for place in data.get("results", [])[:limit]:
                restaurant = {
                    "name": place.get("name"),
                    "address": place.get("formatted_address"),
                    "rating": place.get("rating"),
                    "price_level": place.get("price_level"),
                    "cuisine": self._extract_cuisine(place.get("types", [])),
                    "place_id": place.get("place_id"),
                    "phone": None,  # Would need Place Details API call
                    "website": None,  # Would need Place Details API call
                    "hours": None   # Would need Place Details API call
                }
                results.append(restaurant)
            
            return results
            
        except Exception as e:
            print(f"Error searching restaurants: {e}")
            return self._mock_restaurant_data(location, cuisine)
    
    async def search_hotels(
        self,
        location: str,
        check_in: Optional[str] = None,
        check_out: Optional[str] = None,
        guests: int = 2,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for hotels and accommodations."""
        
        if not self.google_places_key:
            return self._mock_hotel_data(location)
        
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": f"hotels in {location}",
            "key": self.google_places_key,
            "type": "lodging"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for place in data.get("results", [])[:limit]:
                hotel = {
                    "name": place.get("name"),
                    "address": place.get("formatted_address"),
                    "rating": place.get("rating"),
                    "price_level": place.get("price_level"),
                    "place_id": place.get("place_id"),
                    "check_in": check_in,
                    "check_out": check_out,
                    "guests": guests
                }
                results.append(hotel)
            
            return results
            
        except Exception as e:
            print(f"Error searching hotels: {e}")
            return self._mock_hotel_data(location)
    
    async def search_events(
        self,
        location: str,
        date: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for events and activities."""
        
        # For now, return mock data
        # In production, integrate with Eventbrite, Ticketmaster, etc.
        return self._mock_event_data(location, category)
    
    def _extract_cuisine(self, types: List[str]) -> Optional[str]:
        """Extract cuisine type from Google Places types."""
        cuisine_mapping = {
            "italian": "Italian",
            "chinese": "Chinese", 
            "mexican": "Mexican",
            "indian": "Indian",
            "thai": "Thai",
            "japanese": "Japanese",
            "french": "French",
            "american": "American",
            "mediterranean": "Mediterranean"
        }
        
        for place_type in types:
            if place_type in cuisine_mapping:
                return cuisine_mapping[place_type]
        
        return None
    
    def _mock_restaurant_data(self, location: str, cuisine: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return mock restaurant data for testing."""
        cuisine_type = cuisine or "International"
        
        return [
            {
                "name": f"The {cuisine_type} Bistro",
                "address": f"123 Main St, {location}",
                "rating": 4.5,
                "price_level": 2,
                "cuisine": cuisine_type,
                "place_id": "mock_place_1",
                "phone": "(555) 123-4567",
                "website": "https://example.com",
                "hours": "11:00 AM - 10:00 PM"
            },
            {
                "name": f"Gourmet {cuisine_type} Kitchen",
                "address": f"456 Oak Ave, {location}",
                "rating": 4.2,
                "price_level": 3,
                "cuisine": cuisine_type,
                "place_id": "mock_place_2", 
                "phone": "(555) 234-5678",
                "website": "https://example2.com",
                "hours": "5:00 PM - 11:00 PM"
            },
            {
                "name": f"Casual {cuisine_type} Spot",
                "address": f"789 Pine St, {location}",
                "rating": 4.0,
                "price_level": 1,
                "cuisine": cuisine_type,
                "place_id": "mock_place_3",
                "phone": "(555) 345-6789", 
                "website": "https://example3.com",
                "hours": "12:00 PM - 9:00 PM"
            }
        ]
    
    def _mock_hotel_data(self, location: str) -> List[Dict[str, Any]]:
        """Return mock hotel data for testing."""
        return [
            {
                "name": f"Grand {location} Hotel",
                "address": f"100 Hotel Blvd, {location}",
                "rating": 4.6,
                "price_level": 4,
                "place_id": "mock_hotel_1",
                "amenities": ["Pool", "Gym", "Spa", "Restaurant"]
            },
            {
                "name": f"Boutique {location} Inn",
                "address": f"200 Charm St, {location}",
                "rating": 4.3,
                "price_level": 3,
                "place_id": "mock_hotel_2",
                "amenities": ["Free WiFi", "Continental Breakfast", "Pet Friendly"]
            },
            {
                "name": f"Budget {location} Lodge",
                "address": f"300 Economy Dr, {location}",
                "rating": 3.8,
                "price_level": 2,
                "place_id": "mock_hotel_3",
                "amenities": ["Free Parking", "24hr Front Desk"]
            }
        ]
    
    def _mock_event_data(self, location: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return mock event data for testing."""
        event_type = category or "Entertainment"
        
        return [
            {
                "name": f"{location} {event_type} Festival",
                "date": "2024-02-15",
                "time": "7:00 PM",
                "venue": f"{location} Convention Center",
                "category": event_type,
                "price": "$25-$75",
                "description": f"Annual {event_type.lower()} festival featuring local and international acts"
            },
            {
                "name": f"Live {event_type} Night",
                "date": "2024-02-20",
                "time": "8:00 PM", 
                "venue": f"The {location} Theater",
                "category": event_type,
                "price": "$15-$40",
                "description": f"Weekly {event_type.lower()} showcase with emerging artists"
            }
        ]