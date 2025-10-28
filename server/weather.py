from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("weather")

# Constants
GEOCODING_API = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_API = "https://api.open-meteo.com/v1/forecast"


async def make_api_request(url: str, params: dict[str, Any]) -> dict[str, Any] | None:
    """Make a request to the API with proper error handling."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return None


async def get_coordinates(city: str, country: str = "") -> tuple[float, float, str] | None:
    """Get coordinates for a city using geocoding API.
    
    Args:
        city: City name
        country: Optional country name or code for more precise results
    
    Returns:
        Tuple of (latitude, longitude, location_name) or None if not found
    """
    search_query = f"{city}, {country}" if country else city
    params = {
        "name": search_query,
        "count": 1,
        "language": "en",
        "format": "json"
    }
    
    data = await make_api_request(GEOCODING_API, params)
    
    if not data or "results" not in data or not data["results"]:
        return None
    
    result = data["results"][0]
    location_name = f"{result['name']}, {result.get('country', 'Unknown')}"
    return (result["latitude"], result["longitude"], location_name)


@mcp.tool()
async def get_current_weather(city: str, country: str = "") -> str:
    """Get current weather for any city in the world.

    Args:
        city: City name (e.g., "Paris", "Lyon", "Marseille")
        country: Optional country name or code for more precise results (e.g., "France", "FR")
    
    Examples:
        - get_current_weather("Paris", "France")
        - get_current_weather("Lyon")
    """
    coords = await get_coordinates(city, country)
    if not coords:
        return f"Could not find location: {city}" + (f", {country}" if country else "")
    
    latitude, longitude, location_name = coords
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", 
                   "precipitation", "weather_code", "wind_speed_10m", "wind_direction_10m"],
        "timezone": "auto"
    }
    
    data = await make_api_request(WEATHER_API, params)
    
    if not data or "current" not in data:
        return "Unable to fetch weather data."
    
    current = data["current"]
    weather_codes = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
        77: "Snow grains", 80: "Slight rain showers", 81: "Moderate rain showers",
        82: "Violent rain showers", 85: "Slight snow showers", 86: "Heavy snow showers",
        95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
    }
    
    weather_desc = weather_codes.get(current.get("weather_code", 0), "Unknown")
    
    return f"""
Current Weather for {location_name}
{'=' * 50}
Condition: {weather_desc}
Temperature: {current.get('temperature_2m', 'N/A')}°C
Feels Like: {current.get('apparent_temperature', 'N/A')}°C
Humidity: {current.get('relative_humidity_2m', 'N/A')}%
Wind Speed: {current.get('wind_speed_10m', 'N/A')} km/h
Wind Direction: {current.get('wind_direction_10m', 'N/A')}°
Precipitation: {current.get('precipitation', 'N/A')} mm
    """.strip()


@mcp.tool()
async def get_forecast(city: str, country: str = "", days: int = 3) -> str:
    """Get weather forecast for any city in the world.

    Args:
        city: City name (e.g., "Paris", "Lyon", "Marseille")
        country: Optional country name or code for more precise results (e.g., "France", "FR")
        days: Number of days to forecast (1-7, default: 3)
    
    Examples:
        - get_forecast("Paris", "France", 5)
        - get_forecast("Marseille")
    """
    if days < 1 or days > 7:
        return "Days must be between 1 and 7."
    
    coords = await get_coordinates(city, country)
    if not coords:
        return f"Could not find location: {city}" + (f", {country}" if country else "")
    
    latitude, longitude, location_name = coords
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min",
                 "precipitation_sum", "wind_speed_10m_max", "precipitation_probability_max"],
        "timezone": "auto",
        "forecast_days": days
    }
    
    data = await make_api_request(WEATHER_API, params)
    
    if not data or "daily" not in data:
        return "Unable to fetch forecast data."
    
    daily = data["daily"]
    weather_codes = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Foggy", 48: "Depositing rime fog",
        51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
        61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
        95: "Thunderstorm"
    }
    
    result = f"{days}-Day Weather Forecast for {location_name}\n{'=' * 50}\n\n"
    
    for i in range(days):
        date = daily["time"][i]
        weather_code = daily["weather_code"][i]
        weather_desc = weather_codes.get(weather_code, "Unknown")
        temp_max = daily["temperature_2m_max"][i]
        temp_min = daily["temperature_2m_min"][i]
        precip = daily["precipitation_sum"][i]
        wind_max = daily["wind_speed_10m_max"][i]
        precip_prob = daily.get("precipitation_probability_max", [None] * days)[i]
        
        result += f"""Date: {date}
Condition: {weather_desc}
Temperature: {temp_min}°C - {temp_max}°C
Precipitation: {precip} mm"""
        
        if precip_prob is not None:
            result += f" ({precip_prob}% chance)"
        
        result += f"\nMax Wind Speed: {wind_max} km/h\n\n"
    
    return result.strip()


@mcp.resource("echo://{message}")
def echo_resource(message: str) -> str:
    """Echo a message as a resource"""
    return f"Resource echo: {message}"

