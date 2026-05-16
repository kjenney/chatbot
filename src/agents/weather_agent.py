"""
Weather Agent
Fetches current weather information using wttr.in API
"""

from typing import Dict, Any
import requests
from agents.base_agent import BaseAgent


class WeatherAgent(BaseAgent):
    """Sub-agent to fetch weather information"""

    def __init__(self):
        super().__init__(
            name="weather",
            description="Fetches current weather information for a location using wttr.in"
        )

    def execute(self, location: str = "auto", **kwargs) -> Dict[str, Any]:
        """
        Fetch weather data for a location

        Args:
            location: City name or 'auto' for automatic detection
        """
        try:
            # Using wttr.in - no API key needed
            url = f"https://wttr.in/{location}?format=j1"
            response = requests.get(url, timeout=5)
            response.raise_for_status()

            data = response.json()
            current = data['current_condition'][0]

            weather_info = {
                'location': location,
                'temperature_c': current['temp_C'],
                'temperature_f': current['temp_F'],
                'condition': current['weatherDesc'][0]['value'],
                'humidity': current['humidity'],
                'wind_speed_kmh': current['windspeedKmph'],
                'feels_like_c': current['FeelsLikeC'],
                'feels_like_f': current['FeelsLikeF']
            }

            return {
                'success': True,
                'data': weather_info
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to fetch weather: {str(e)}"
            }
