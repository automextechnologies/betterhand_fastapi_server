import logging
import httpx
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

async def calculate_driving_distance_and_eta(
    orig_lat: float, orig_lon: float, dest_lat: float, dest_lon: float
) -> Optional[Dict[str, Any]]:
    """
    Call OpenRouteService to calculate driving distance and duration between two points.
    Returns a dict with 'distance_meters' and 'duration_seconds' or None.
    """
    api_key = settings.ORS_API_KEY
    if not api_key or "your-ors-api-key" in api_key:
        logger.warning("No valid ORS API key configured — skipping API call.")
        return None
        
    url = "https://api.openrouteservice.org/v2/directions/driving-car/json"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "coordinates": [
            [float(orig_lon), float(orig_lat)],
            [float(dest_lon), float(dest_lat)]
        ]
    }
    
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                route = data["routes"][0]
                segment = route["segments"][0]
                return {
                    "distance_meters": segment["distance"],
                    "duration_seconds": segment["duration"],
                    "geometry": route.get("geometry")
                }
            else:
                logger.error(f"ORS API returned status code {response.status_code}: {response.text}")
                return None
    except Exception as e:
        logger.error(f"Error calling OpenRouteService API: {e}")
        return None
