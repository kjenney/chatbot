"""
Calculator Agent
Performs mathematical calculations safely
"""

from typing import Dict, Any
from agents.base_agent import BaseAgent


class CalculatorAgent(BaseAgent):
    """Sub-agent to perform calculations"""

    def __init__(self):
        super().__init__(
            name="calculator",
            description="Performs mathematical calculations"
        )

    def execute(self, expression: str, **kwargs) -> Dict[str, Any]:
        """
        Evaluate a mathematical expression

        Args:
            expression: Mathematical expression to evaluate
        """
        try:
            # Safe evaluation of mathematical expressions
            # Remove any dangerous operations
            allowed_chars = set('0123456789+-*/().%** ')
            if not all(c in allowed_chars for c in expression):
                return {
                    'success': False,
                    'error': 'Expression contains invalid characters'
                }

            result = eval(expression, {"__builtins__": {}}, {})

            return {
                'success': True,
                'data': {
                    'expression': expression,
                    'result': result
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Calculation failed: {str(e)}"
            }
