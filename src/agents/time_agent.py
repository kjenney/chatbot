"""
Time Agent
Gets current date and time information
"""

from typing import Dict, Any
from datetime import datetime
from agents.base_agent import BaseAgent


class TimeAgent(BaseAgent):
    """Sub-agent to get current time information"""

    def __init__(self):
        super().__init__(
            name="time",
            description="Gets current date and time information"
        )

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Get current time information"""
        try:
            now = datetime.now()

            time_info = {
                'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
                'date': now.strftime('%Y-%m-%d'),
                'time': now.strftime('%H:%M:%S'),
                'day_of_week': now.strftime('%A'),
                'timestamp': now.timestamp()
            }

            return {
                'success': True,
                'data': time_info
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to get time: {str(e)}"
            }
