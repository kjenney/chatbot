#!/usr/bin/env python3
"""
Sub-Agent Framework
Orchestrates multiple sub-agents running in parallel processes

This module provides the orchestration layer for the plugin-based agent system.
Individual agents are automatically discovered from the agents/ directory.
"""

from typing import Dict, Any, List
from multiprocessing import Process, Queue
import time
from agents import available_agents, list_agents as get_agent_list


class AgentOrchestrator:
    """Orchestrates multiple sub-agents running in parallel"""

    def __init__(self):
        # Use auto-discovered agents from the agents module
        self.agents = available_agents

    def execute_agents(self, agent_tasks: List[Dict[str, Any]], timeout: int = 10) -> List[Dict[str, Any]]:
        """
        Execute multiple agents in parallel

        Args:
            agent_tasks: List of dicts with 'agent' name and 'params' dict
            timeout: Maximum seconds to wait for all agents

        Returns:
            List of results from each agent
        """
        if not agent_tasks:
            return []

        result_queue = Queue()
        processes = []

        # Start all agent processes
        for task in agent_tasks:
            agent_name = task.get('agent')
            params = task.get('params', {})

            if agent_name not in self.agents:
                result_queue.put({
                    'agent': agent_name,
                    'success': False,
                    'error': f"Unknown agent: {agent_name}"
                })
                continue

            agent = self.agents[agent_name]
            process = Process(
                target=agent.run_in_process,
                args=(result_queue,),
                kwargs=params
            )
            process.start()
            processes.append(process)

        # Collect results
        results = []
        start_time = time.time()

        for _ in range(len(processes)):
            remaining_time = timeout - (time.time() - start_time)
            if remaining_time <= 0:
                break

            try:
                result = result_queue.get(timeout=remaining_time)
                results.append(result)
            except:
                break

        # Cleanup processes
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=1)
                if process.is_alive():
                    process.kill()

        return results

    def list_agents(self) -> List[Dict[str, str]]:
        """List all available agents and their descriptions"""
        return [
            {
                'name': name,
                'description': agent.description
            }
            for name, agent in self.agents.items()
        ]


# Convenience function for simple single-agent execution
def execute_agent(agent_name: str, timeout: int = 10, **params) -> Dict[str, Any]:
    """
    Execute a single agent

    Args:
        agent_name: Name of the agent to execute
        timeout: Maximum seconds to wait
        **params: Parameters to pass to the agent

    Returns:
        Agent result dictionary
    """
    orchestrator = AgentOrchestrator()
    results = orchestrator.execute_agents(
        [{'agent': agent_name, 'params': params}],
        timeout=timeout
    )

    return results[0] if results else {
        'agent': agent_name,
        'success': False,
        'error': 'Agent execution timed out'
    }


# Expose the agents list for compatibility
def list_agents() -> List[Dict[str, str]]:
    """List all available agents"""
    agent_info = get_agent_list()
    return [
        {'name': name, 'description': desc}
        for name, desc in agent_info.items()
    ]
