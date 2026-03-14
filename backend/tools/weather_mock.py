import re
import random
from datetime import datetime
from .base import BaseTool, ToolResult


WEATHER_DB: dict[str, dict] = {
    "london": {"condition": "Overcast", "temp_c": 12, "humidity": 82, "wind_kph": 18, "emoji": "☁️"},
    "new york": {"condition": "Partly Cloudy", "temp_c": 18, "humidity": 65, "wind_kph": 22, "emoji": "⛅"},
    "tokyo": {"condition": "Clear", "temp_c": 24, "humidity": 58, "wind_kph": 10, "emoji": "☀️"},
    "sydney": {"condition": "Sunny", "temp_c": 28, "humidity": 55, "wind_kph": 14, "emoji": "☀️"},
    "paris": {"condition": "Light Rain", "temp_c": 15, "humidity": 78, "wind_kph": 20, "emoji": "🌧️"},
    "berlin": {"condition": "Cloudy", "temp_c": 10, "humidity": 75, "wind_kph": 25, "emoji": "☁️"},
    "dubai": {"condition": "Sunny", "temp_c": 38, "humidity": 40, "wind_kph": 8, "emoji": "☀️"},
    "moscow": {"condition": "Snow", "temp_c": -3, "humidity": 88, "wind_kph": 30, "emoji": "❄️"},
    "toronto": {"condition": "Partly Cloudy", "temp_c": 9, "humidity": 68, "wind_kph": 16, "emoji": "⛅"},
    "singapore": {"condition": "Thunderstorm", "temp_c": 30, "humidity": 90, "wind_kph": 35, "emoji": "⛈️"},
    "los angeles": {"condition": "Sunny", "temp_c": 26, "humidity": 45, "wind_kph": 11, "emoji": "☀️"},
    "chicago": {"condition": "Windy", "temp_c": 14, "humidity": 60, "wind_kph": 45, "emoji": "💨"},
    "mumbai": {"condition": "Humid and Hazy", "temp_c": 33, "humidity": 85, "wind_kph": 12, "emoji": "🌫️"},
    "cairo": {"condition": "Sunny", "temp_c": 35, "humidity": 30, "wind_kph": 15, "emoji": "☀️"},
    "amsterdam": {"condition": "Light Drizzle", "temp_c": 11, "humidity": 80, "wind_kph": 22, "emoji": "🌦️"},
    "seoul": {"condition": "Clear", "temp_c": 20, "humidity": 55, "wind_kph": 12, "emoji": "☀️"},
    "bangkok": {"condition": "Hot and Humid", "temp_c": 34, "humidity": 88, "wind_kph": 9, "emoji": "🌤️"},
    "cape town": {"condition": "Windy", "temp_c": 22, "humidity": 62, "wind_kph": 38, "emoji": "💨"},
    "rome": {"condition": "Sunny", "temp_c": 23, "humidity": 50, "wind_kph": 13, "emoji": "☀️"},
    "beijing": {"condition": "Smoggy", "temp_c": 19, "humidity": 70, "wind_kph": 20, "emoji": "🌫️"},
}

GENERIC_CONDITIONS = [
    {"condition": "Partly Cloudy", "temp_c": 17, "humidity": 65, "wind_kph": 15, "emoji": "⛅"},
    {"condition": "Sunny", "temp_c": 22, "humidity": 50, "wind_kph": 12, "emoji": "☀️"},
    {"condition": "Overcast", "temp_c": 13, "humidity": 75, "wind_kph": 20, "emoji": "☁️"},
    {"condition": "Light Rain", "temp_c": 11, "humidity": 80, "wind_kph": 18, "emoji": "🌧️"},
]


class WeatherMockTool(BaseTool):
    """Returns mock weather data for a given city."""

    @property
    def name(self) -> str:
        return "WeatherMockTool"

    @property
    def description(self) -> str:
        return "Returns mock weather for a city: temperature, condition, humidity, wind"

    @property
    def keywords(self) -> list[str]:
        return [
            "weather", "temperature", "forecast", "rain", "sunny",
            "cloudy", "humidity", "wind", "climate", "degrees",
            "hot", "cold", "storm", "snow",
        ]

    def execute(self, input_text: str) -> ToolResult:
        steps = [f'Received input: "{input_text}"']
        steps.append("Selected tool: WeatherMockTool")

        city = self._extract_city(input_text)

        # Fail early if no city name could be extracted at all
        if not city:
            steps.append("Error: no city name found in input")
            return ToolResult(
                output=None,
                steps=steps,
                error="No city name found in your request. Try: \"weather in London\" or \"forecast for Tokyo\".",
            )

        steps.append(f"Extracted city name: \"{city}\"")

        city_key = city.lower().strip()
        data = WEATHER_DB.get(city_key)

        if data:
            steps.append(f"Found city in weather database: {city}")
        else:
            # Fuzzy match — check if any known city is a substring
            for known_city, known_data in WEATHER_DB.items():
                if known_city in city_key or city_key in known_city:
                    data = known_data
                    city = known_city.title()
                    steps.append(f"Fuzzy matched city: \"{city}\"")
                    break

        if not data:
            data = random.choice(GENERIC_CONDITIONS)
            steps.append(f"City not in database, generating mock data for \"{city}\"")

        temp_f = round(data["temp_c"] * 9 / 5 + 32, 1)
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

        result = (
            f"{data['emoji']} Weather in {city.title()}\n"
            f"Condition: {data['condition']}\n"
            f"Temperature: {data['temp_c']}°C / {temp_f}°F\n"
            f"Humidity: {data['humidity']}%\n"
            f"Wind: {data['wind_kph']} km/h\n"
            f"As of: {timestamp} (mock data)"
        )

        steps.append(f"Assembled weather report for {city.title()}")
        steps.append("Returning result to user")
        return ToolResult(output=result, steps=steps)

    def _extract_city(self, text: str) -> str:
        """Extract city name from text like 'weather in London' or 'what's the weather for Tokyo'."""
        patterns = [
            r'weather\s+(?:in|for|at|of)\s+([a-zA-Z\s]+?)(?:\?|$|\.)',
            r'(?:in|for|at)\s+([A-Z][a-zA-Z\s]+?)(?:\?|$|\.|\s+today|\s+now)',
            r'forecast\s+(?:for|in)\s+([a-zA-Z\s]+?)(?:\?|$|\.)',
            r'temperature\s+(?:in|for|at)\s+([a-zA-Z\s]+?)(?:\?|$|\.)',
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()

        # Last resort: strip command words and return remainder
        stripped = re.sub(
            r'\b(weather|forecast|temperature|what|is|the|in|for|at|of|today|now|get|show|tell|me|degrees|celsius|fahrenheit)\b',
            '', text, flags=re.IGNORECASE
        )
        city = re.sub(r'[^a-zA-Z\s]', '', stripped).strip()
        # Return empty string if nothing meaningful found — execute() checks for this
        return city
