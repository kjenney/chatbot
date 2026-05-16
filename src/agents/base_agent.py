"""
Base Agent Class
All sub-agents must inherit from this class
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from multiprocessing import Queue


class BaseAgent(ABC):
    """Base class for all sub-agents"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the agent's task

        Returns:
            Dict with 'success', 'data', and optional 'error' keys
        """
        pass

    def run_in_process(self, result_queue: Queue, **kwargs):
        """Wrapper to run execute in a separate process"""
        try:
            result = self.execute(**kwargs)
            result_queue.put({
                'agent': self.name,
                'success': True,
                'data': result
            })
        except Exception as e:
            result_queue.put({
                'agent': self.name,
                'success': False,
                'error': str(e)
            })
