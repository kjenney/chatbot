"""
Agent Plugin System
Automatically discovers and loads all agents in the agents directory
"""

import os
import importlib
import inspect
from typing import Dict, Type
from agents.base_agent import BaseAgent


def discover_agents() -> Dict[str, Type[BaseAgent]]:
    """
    Automatically discover all agent classes in the agents directory

    Returns:
        Dictionary mapping agent names to agent classes
    """
    agents = {}
    agents_dir = os.path.dirname(__file__)

    # Get all Python files in the agents directory
    for filename in os.listdir(agents_dir):
        if filename.endswith('_agent.py'):
            module_name = filename[:-3]  # Remove .py extension

            try:
                # Import the module
                module = importlib.import_module(f'agents.{module_name}')

                # Find all classes that inherit from BaseAgent
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseAgent) and
                        obj is not BaseAgent and
                        obj.__module__ == f'agents.{module_name}'):

                        # Instantiate the agent
                        agent_instance = obj()
                        agents[agent_instance.name] = agent_instance

            except Exception as e:
                print(f"Warning: Failed to load agent from {filename}: {str(e)}")
                continue

    return agents


# Auto-discover agents when the module is imported
available_agents = discover_agents()


def get_agent(name: str) -> BaseAgent:
    """
    Get an agent instance by name

    Args:
        name: The agent name

    Returns:
        Agent instance

    Raises:
        KeyError: If agent not found
    """
    return available_agents[name]


def list_agents() -> Dict[str, str]:
    """
    List all available agents and their descriptions

    Returns:
        Dictionary mapping agent names to descriptions
    """
    return {
        name: agent.description
        for name, agent in available_agents.items()
    }


__all__ = ['BaseAgent', 'discover_agents', 'get_agent', 'list_agents', 'available_agents']
