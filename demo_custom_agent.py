#!/usr/bin/env python3
"""
Demo: Creating a Custom Agent
Shows how easy it is to add new agents to the system
"""

# Step 1: Test current agents
print("=" * 60)
print("STEP 1: Current Available Agents")
print("=" * 60)

from agents import list_agents

agents = list_agents()
print(f"\nFound {len(agents)} agents:")
for name, desc in agents.items():
    print(f"  • {name}: {desc}")

# Step 2: Create a custom agent file
print("\n\n" + "=" * 60)
print("STEP 2: Creating a Custom 'Joke' Agent")
print("=" * 60)

custom_agent_code = '''"""
Joke Agent
Tells programming jokes
"""

from typing import Dict, Any
import random
from agents.base_agent import BaseAgent


class JokeAgent(BaseAgent):
    """Tells programming jokes"""

    def __init__(self):
        super().__init__(
            name="joke",
            description="Tells random programming jokes"
        )

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Tell a random programming joke"""
        try:
            jokes = [
                "Why do programmers prefer dark mode? Because light attracts bugs!",
                "How many programmers does it take to change a light bulb? None, that's a hardware problem.",
                "Why did the programmer quit his job? He didn't get arrays!",
                "What's a programmer's favorite hangout place? The Foo Bar!",
                "Why do Java developers wear glasses? Because they can't C#!"
            ]

            return {
                'success': True,
                'data': {
                    'joke': random.choice(jokes)
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
'''

# Write the custom agent
import os

agent_file_path = 'agents/joke_agent.py'
print(f"\nCreating agent file: {agent_file_path}")
print("\nAgent code:")
print("-" * 60)
print(custom_agent_code)
print("-" * 60)

with open(agent_file_path, 'w') as f:
    f.write(custom_agent_code)

print(f"\n✓ Agent file created!")

# Step 3: Test the new agent
print("\n\n" + "=" * 60)
print("STEP 3: Testing the New Agent")
print("=" * 60)

# Need to reimport to pick up the new agent
import importlib
import agents
importlib.reload(agents)

# Check if agent is discovered
from agents import list_agents as get_agents_fresh
new_agents = get_agents_fresh()

print(f"\nFound {len(new_agents)} agents (should be {len(agents) + 1}):")
for name, desc in new_agents.items():
    marker = "✨ NEW!" if name == "joke" else ""
    print(f"  • {name}: {desc} {marker}")

# Test the agent directly
if 'joke' in new_agents:
    print("\n" + "-" * 60)
    print("Testing the joke agent...")
    print("-" * 60)

    from sub_agents import execute_agent

    result = execute_agent('joke')

    if result['success']:
        print(f"\n🎭 Joke: {result['data']['data']['joke']}")
        print("\n✓ Agent works perfectly!")
    else:
        print(f"\n✗ Error: {result.get('error')}")
else:
    print("\n✗ Agent not discovered (may need to restart Python)")

# Step 4: Show how to clean up
print("\n\n" + "=" * 60)
print("STEP 4: Cleanup")
print("=" * 60)

cleanup = input("\nRemove the demo agent? (y/n): ").lower()
if cleanup == 'y':
    os.remove(agent_file_path)
    print(f"✓ Removed {agent_file_path}")
else:
    print(f"✓ Kept {agent_file_path} - you can use it or delete it later")

print("\n" + "=" * 60)
print("DEMO COMPLETE!")
print("=" * 60)

print("""
Key Takeaways:
1. Create a file: agents/your_agent.py
2. Inherit from BaseAgent
3. Implement execute() method
4. That's it! Auto-discovered and ready to use

No imports, no registration, no restarts needed (in production).

Try it yourself:
1. Create agents/your_agent.py
2. Copy the template from PLUGIN_GUIDE.md
3. Implement your logic
4. Test with: execute_agent('your_agent')

The plugin system handles everything else!
""")
