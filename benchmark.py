#!/usr/bin/env python3
"""
Agent Benchmarking System
Measures agent correctness, response quality, and latency over time
"""

import json
import time
import sqlite3
import argparse
import re
import glob
from datetime import datetime
from typing import Dict, List, Tuple, Any
from uuid import uuid4
from chatbot_agent import PersistentChatbot
from tabulate import tabulate


class BenchmarkRunner:
    """Runs benchmarks and stores results in SQLite"""

    def __init__(self, db_path: str = "web_chatbot.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.chatbot = None
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        """Create benchmark_results table if it doesn't exist"""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                timestamp TEXT,
                agent_name TEXT,
                case_id TEXT,
                input TEXT,
                response TEXT,
                correctness REAL,
                latency_ms INTEGER,
                passed INTEGER,
                model TEXT
            )
        """)
        self.conn.commit()

    def _get_chatbot(self, model: str = "qwen3:8b") -> PersistentChatbot:
        """Lazy load chatbot instance"""
        if self.chatbot is None:
            self.chatbot = PersistentChatbot(db_path=self.db_path, enable_sub_agents=True, model=model)
        return self.chatbot

    def load_cases(self, agent_name: str = None) -> Dict[str, List[Dict]]:
        """Load test cases from benchmark JSON files"""
        cases_by_agent = {}

        # Glob all benchmark JSON files
        benchmark_files = glob.glob("benchmarks/*_benchmark.json")

        if not benchmark_files:
            print("Error: No benchmark files found in benchmarks/ directory")
            return {}

        for filepath in benchmark_files:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    loaded_agent = data.get('agent')

                    # Skip if filtering by agent and this isn't it
                    if agent_name and loaded_agent != agent_name:
                        continue

                    cases_by_agent[loaded_agent] = data.get('cases', [])
            except Exception as e:
                print(f"Warning: Failed to load {filepath}: {e}")

        return cases_by_agent

    def score(self, response: str, expected_keywords: List[str], expected_patterns: List[str]) -> float:
        """
        Score response based on keyword/pattern matching

        Returns: 0.0 to 1.0 float
        """
        if not expected_keywords and not expected_patterns:
            return 1.0  # No expectations = perfect score

        matches = 0
        total = len(expected_keywords) + len(expected_patterns)

        # Check keywords (case-insensitive)
        response_lower = response.lower()
        for keyword in expected_keywords:
            if keyword.lower() in response_lower:
                matches += 1

        # Check patterns (regex)
        for pattern in expected_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                matches += 1

        return matches / total if total > 0 else 1.0

    def run_case(self, agent_name: str, case: Dict[str, Any], run_id: str, model: str) -> Dict[str, Any]:
        """Run a single benchmark case"""
        start_time = time.time()

        try:
            # Call chatbot with the test input
            chatbot = self._get_chatbot(model)
            response = chatbot.respond(case['input'], model=model)
            latency_ms = int((time.time() - start_time) * 1000)

            # Score the response
            correctness = self.score(response, case.get('expected_keywords', []), case.get('expected_patterns', []))

            # Check if it passed
            max_latency = case.get('max_latency_ms', 30000)
            passed = (correctness == 1.0) and (latency_ms <= max_latency)

            return {
                'agent_name': agent_name,
                'case_id': case['id'],
                'input': case['input'],
                'response': response,
                'correctness': correctness,
                'latency_ms': latency_ms,
                'passed': 1 if passed else 0,
                'status': 'PASS' if passed else 'FAIL'
            }

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return {
                'agent_name': agent_name,
                'case_id': case['id'],
                'input': case['input'],
                'response': f'ERROR: {str(e)}',
                'correctness': 0.0,
                'latency_ms': latency_ms,
                'passed': 0,
                'status': 'ERROR'
            }

    def store_result(self, run_id: str, result: Dict[str, Any], model: str):
        """Store benchmark result in SQLite"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO benchmark_results
            (run_id, timestamp, agent_name, case_id, input, response, correctness, latency_ms, passed, model)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            datetime.now().isoformat(),
            result['agent_name'],
            result['case_id'],
            result['input'],
            result['response'],
            result['correctness'],
            result['latency_ms'],
            result['passed'],
            model
        ))
        self.conn.commit()

    def run_all(self, agent_name: str = None, model: str = "qwen3:8b") -> Dict[str, List[Dict]]:
        """Run all benchmark cases"""
        run_id = str(uuid4())
        cases_by_agent = self.load_cases(agent_name)

        if not cases_by_agent:
            print("Error: No benchmark cases loaded")
            return {}

        all_results = {}

        for agent, cases in cases_by_agent.items():
            print(f"\nRunning {agent} agent benchmarks...")
            agent_results = []

            for case in cases:
                result = self.run_case(agent, case, run_id, model)
                agent_results.append(result)
                self.store_result(run_id, result, model)

                status_symbol = "✓" if result['status'] == 'PASS' else "✗"
                print(f"  {status_symbol} {case['id']}: {result['status']} ({result['latency_ms']}ms, correctness: {result['correctness']:.2f})")

            all_results[agent] = agent_results

        return all_results

    def print_results(self, results: Dict[str, List[Dict]]):
        """Print benchmark results as a table"""
        print("\n" + "=" * 100)
        print("BENCHMARK RESULTS")
        print("=" * 100)

        for agent, cases in results.items():
            print(f"\n{agent.upper()}")
            print("-" * 100)

            table_data = []
            for case in cases:
                table_data.append([
                    case['case_id'],
                    case['status'],
                    f"{case['latency_ms']}ms",
                    f"{case['correctness']:.2f}",
                    case['input'][:50] + "..." if len(case['input']) > 50 else case['input']
                ])

            print(tabulate(table_data, headers=['Case ID', 'Status', 'Latency', 'Correctness', 'Input'], tablefmt='grid'))

            # Summary stats
            passed = sum(1 for case in cases if case['passed'])
            total = len(cases)
            avg_latency = sum(case['latency_ms'] for case in cases) / len(cases) if cases else 0

            print(f"\nSummary: {passed}/{total} passed ({100*passed//total}%), avg latency: {avg_latency:.0f}ms")

    def report(self, limit_runs: int = 10):
        """Print historical benchmark report"""
        cursor = self.conn.cursor()

        # Get unique run IDs (limit to last N runs)
        cursor.execute("""
            SELECT DISTINCT run_id FROM benchmark_results
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit_runs,))

        run_ids = [row[0] for row in cursor.fetchall()]

        if not run_ids:
            print("No benchmark history found")
            return

        print("\n" + "=" * 100)
        print("BENCHMARK HISTORY REPORT")
        print("=" * 100)

        # Group by agent
        cursor.execute("""
            SELECT agent_name, COUNT(*) as total, SUM(passed) as passed, AVG(latency_ms) as avg_latency
            FROM benchmark_results
            WHERE run_id IN ({})
            GROUP BY agent_name
            ORDER BY agent_name
        """.format(','.join('?' * len(run_ids))), run_ids)

        table_data = []
        for row in cursor.fetchall():
            agent, total, passed, avg_latency = row
            pass_rate = 100 * (passed or 0) // total if total > 0 else 0
            table_data.append([
                agent,
                f"{passed or 0}/{total}",
                f"{pass_rate}%",
                f"{avg_latency:.0f}ms"
            ])

        print("\nPer-Agent Summary (across last {} runs):".format(len(run_ids)))
        print(tabulate(table_data, headers=['Agent', 'Passed', 'Pass Rate', 'Avg Latency'], tablefmt='grid'))

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
        if self.chatbot:
            self.chatbot.close()


def main():
    parser = argparse.ArgumentParser(description='Benchmark AI chatbot agents')
    parser.add_argument('--agent', type=str, help='Run benchmarks for specific agent only')
    parser.add_argument('--report', action='store_true', help='Show historical benchmark report')
    parser.add_argument('--model', type=str, default='qwen3:8b', help='Ollama model to use')

    args = parser.parse_args()

    runner = BenchmarkRunner()

    try:
        if args.report:
            runner.report()
        else:
            results = runner.run_all(agent_name=args.agent, model=args.model)
            runner.print_results(results)
    finally:
        runner.close()


if __name__ == '__main__':
    main()
