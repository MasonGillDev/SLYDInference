"""
Benchmarking utilities for vLLM model testing
"""
import time
import asyncio
import aiohttp
import numpy as np
from typing import Dict, List, Any
import json
import random
from concurrent.futures import ThreadPoolExecutor
import requests
from datetime import datetime

class ModelBenchmark:
    def __init__(self, base_url: str, model_name: str):
        self.base_url = base_url
        self.model_name = model_name
        self.chat_endpoint = f"{base_url}/v1/chat/completions"
        
        # Test prompts of varying lengths - base templates
        self.test_prompts = {
            "short": [
                "What is {}+{}?",
                "Define the word '{}'",
                "What year was {} founded?",
                "How many {} are in a {}?",
                "What is the capital of {}?"
            ],
            "medium": [
                "Explain the concept of {} in simple terms. Include examples.",
                "What are the main differences between {} and {}?",
                "Describe the process of {} and its importance.",
                "List {} benefits of {} and explain each briefly.",
                "How does {} affect {} in modern society?"
            ],
            "long": [
                "Write a detailed analysis of {}. Consider multiple perspectives and provide examples.",
                "Discuss the historical development of {} from {} to present day.",
                "Compare and contrast {} approaches to {}. Include advantages and disadvantages.",
                "Analyze the impact of {} on {}. Consider economic, social, and environmental factors.",
                "Explain how {} works, its applications, and future potential in the field of {}."
            ]
        }
        
        # Random words for generating unique prompts
        self.random_words = {
            "concepts": ["democracy", "quantum computing", "blockchain", "evolution", "capitalism", 
                        "artificial intelligence", "climate change", "renewable energy", "genetics"],
            "numbers": list(range(1, 100)),
            "companies": ["Apple", "Google", "Microsoft", "Amazon", "Tesla", "IBM", "Intel"],
            "countries": ["France", "Japan", "Brazil", "Canada", "Australia", "India", "Germany"],
            "objects": ["dozen", "kilometer", "gallon", "century", "byte", "atom"],
            "fields": ["medicine", "education", "technology", "agriculture", "finance", "transportation"]
        }
    
    def generate_unique_prompt(self, prompt_type: str) -> str:
        """Generate a unique prompt by filling in template with random values"""
        templates = self.test_prompts[prompt_type]
        template = random.choice(templates)
        
        # Fill in the template based on its requirements
        if prompt_type == "short":
            if "{}+{}" in template:
                return template.format(random.randint(1, 100), random.randint(1, 100))
            elif "word" in template:
                return template.format(random.choice(self.random_words["concepts"]))
            elif "founded" in template:
                return template.format(random.choice(self.random_words["companies"]))
            elif "How many" in template:
                return template.format(random.choice(self.random_words["objects"]), 
                                     random.choice(self.random_words["objects"]))
            else:  # capital
                return template.format(random.choice(self.random_words["countries"]))
        
        elif prompt_type == "medium":
            concept1 = random.choice(self.random_words["concepts"])
            concept2 = random.choice(self.random_words["concepts"])
            field = random.choice(self.random_words["fields"])
            num = random.randint(3, 7)
            
            if "differences between" in template:
                return template.format(concept1, concept2)
            elif "List {}" in template:
                return template.format(num, concept1)
            elif "How does" in template:
                return template.format(concept1, field)
            else:
                return template.format(concept1)
        
        else:  # long
            concept1 = random.choice(self.random_words["concepts"])
            concept2 = random.choice(self.random_words["concepts"])
            field1 = random.choice(self.random_words["fields"])
            field2 = random.choice(self.random_words["fields"])
            year = random.randint(1900, 2020)
            
            if "historical development" in template:
                return template.format(concept1, year)
            elif "Compare and contrast" in template:
                return template.format(random.randint(2, 5), concept1)
            elif "impact of" in template:
                return template.format(concept1, field1)
            elif "future potential" in template:
                return template.format(concept1, field1)
            else:
                return template.format(concept1)
    
    async def single_request(self, session: aiohttp.ClientSession, prompt: str, max_tokens: int = 256) -> Dict:
        """Execute a single request and measure metrics"""
        start_time = time.time()
        first_token_time = None
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            async with session.post(self.chat_endpoint, json=payload) as response:
                first_byte_time = time.time() - start_time
                result = await response.json()
                total_time = time.time() - start_time
                
                if response.status == 200:
                    usage = result.get('usage', {})
                    return {
                        "success": True,
                        "total_time": total_time,
                        "first_byte_time": first_byte_time,
                        "prompt_tokens": usage.get('prompt_tokens', 0),
                        "completion_tokens": usage.get('completion_tokens', 0),
                        "total_tokens": usage.get('total_tokens', 0),
                        "tokens_per_second": usage.get('completion_tokens', 0) / total_time if total_time > 0 else 0
                    }
                else:
                    return {"success": False, "error": f"Status {response.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def latency_test(self, num_requests: int = 10) -> Dict:
        """Test latency with sequential requests"""
        results = []
        async with aiohttp.ClientSession() as session:
            for i in range(num_requests):
                # Use different prompt lengths with unique content
                prompt_type = ["short", "medium", "long"][i % 3]
                prompt = self.generate_unique_prompt(prompt_type)
                
                result = await self.single_request(session, prompt)
                if result["success"]:
                    results.append(result)
                
                # Small delay between requests
                await asyncio.sleep(0.1)
        
        if not results:
            return {"error": "No successful requests"}
        
        latencies = [r["total_time"] for r in results]
        first_byte_times = [r["first_byte_time"] for r in results]
        tokens_per_sec = [r["tokens_per_second"] for r in results]
        
        return {
            "test_type": "latency",
            "num_requests": len(results),
            "success_rate": len(results) / num_requests * 100,
            "latency": {
                "mean": np.mean(latencies),
                "median": np.median(latencies),
                "p95": np.percentile(latencies, 95),
                "p99": np.percentile(latencies, 99),
                "min": np.min(latencies),
                "max": np.max(latencies)
            },
            "time_to_first_byte": {
                "mean": np.mean(first_byte_times),
                "median": np.median(first_byte_times)
            },
            "throughput": {
                "mean_tokens_per_second": np.mean(tokens_per_sec),
                "max_tokens_per_second": np.max(tokens_per_sec),
                "total_tokens": sum(r["total_tokens"] for r in results),
                "prompt_tokens": sum(r["prompt_tokens"] for r in results),
                "completion_tokens": sum(r["completion_tokens"] for r in results)
            }
        }
    
    async def concurrent_test(self, num_concurrent: int = 5, requests_per_client: int = 3) -> Dict:
        """Test concurrent request handling"""
        start_time = time.time()
        
        async def client_task(client_id: int):
            results = []
            async with aiohttp.ClientSession() as session:
                for i in range(requests_per_client):
                    prompt_type = ["short", "medium", "long"][i % 3]
                    prompt = self.generate_unique_prompt(prompt_type)
                    result = await self.single_request(session, prompt)
                    results.append(result)
            return results
        
        # Launch concurrent clients
        tasks = [client_task(i) for i in range(num_concurrent)]
        all_results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        
        # Flatten results
        flat_results = [r for client_results in all_results for r in client_results]
        successful = [r for r in flat_results if r.get("success")]
        
        if not successful:
            return {"error": "No successful requests"}
        
        latencies = [r["total_time"] for r in successful]
        tokens_per_sec = [r["tokens_per_second"] for r in successful]
        
        return {
            "test_type": "concurrent",
            "num_concurrent_clients": num_concurrent,
            "requests_per_client": requests_per_client,
            "total_requests": num_concurrent * requests_per_client,
            "successful_requests": len(successful),
            "success_rate": len(successful) / len(flat_results) * 100,
            "total_test_time": total_time,
            "requests_per_second": len(successful) / total_time,
            "latency_under_load": {
                "mean": np.mean(latencies),
                "median": np.median(latencies),
                "p95": np.percentile(latencies, 95),
                "p99": np.percentile(latencies, 99)
            },
            "throughput_under_load": {
                "mean_tokens_per_second": np.mean(tokens_per_sec),
                "aggregate_tokens_per_second": sum(tokens_per_sec),
                "total_tokens_processed": sum(r["total_tokens"] for r in successful)
            }
        }
    
    async def throughput_test(self, duration_seconds: int = 30) -> Dict:
        """Test maximum throughput over a time period"""
        start_time = time.time()
        end_time = start_time + duration_seconds
        results = []
        request_count = 0
        
        async with aiohttp.ClientSession() as session:
            while time.time() < end_time:
                # Launch batch of concurrent requests
                batch_size = 10
                tasks = []
                for _ in range(batch_size):
                    prompt_type = random.choice(["short", "medium", "long"])
                    prompt = self.generate_unique_prompt(prompt_type)
                    tasks.append(self.single_request(session, prompt, max_tokens=128))
                
                batch_results = await asyncio.gather(*tasks)
                results.extend(batch_results)
                request_count += batch_size
                
                # Brief pause to avoid overwhelming
                await asyncio.sleep(0.5)
        
        actual_duration = time.time() - start_time
        successful = [r for r in results if r.get("success")]
        
        if not successful:
            return {"error": "No successful requests"}
        
        total_tokens = sum(r["total_tokens"] for r in successful)
        completion_tokens = sum(r["completion_tokens"] for r in successful)
        
        return {
            "test_type": "throughput",
            "test_duration": actual_duration,
            "total_requests": request_count,
            "successful_requests": len(successful),
            "success_rate": len(successful) / len(results) * 100,
            "requests_per_second": len(successful) / actual_duration,
            "tokens_per_second": completion_tokens / actual_duration,
            "total_tokens_processed": total_tokens,
            "average_tokens_per_request": total_tokens / len(successful) if successful else 0
        }
    
    async def stress_test(self, max_concurrent: int = 20) -> Dict:
        """Gradually increase load to find breaking point"""
        results = []
        
        for concurrent in [1, 5, 10, 15, max_concurrent]:
            print(f"Testing with {concurrent} concurrent clients...")
            test_result = await self.concurrent_test(concurrent, requests_per_client=2)
            
            results.append({
                "concurrent_clients": concurrent,
                "success_rate": test_result.get("success_rate", 0),
                "mean_latency": test_result.get("latency_under_load", {}).get("mean", 0),
                "p99_latency": test_result.get("latency_under_load", {}).get("p99", 0),
                "requests_per_second": test_result.get("requests_per_second", 0)
            })
            
            # Stop if success rate drops below 50%
            if test_result.get("success_rate", 0) < 50:
                break
        
        return {
            "test_type": "stress",
            "max_concurrent_tested": max_concurrent,
            "results_by_load": results,
            "optimal_concurrent": max(results, key=lambda x: x["requests_per_second"])["concurrent_clients"],
            "max_sustainable_load": max([r["concurrent_clients"] for r in results if r["success_rate"] > 90], default=1)
        }

async def run_benchmark_suite(base_url: str, model_name: str, tests: List[str]) -> Dict:
    """Run selected benchmark tests"""
    benchmark = ModelBenchmark(base_url, model_name)
    results = {
        "timestamp": datetime.now().isoformat(),
        "model": model_name,
        "base_url": base_url,
        "tests": {}
    }
    
    for test_name in tests:
        print(f"Running {test_name} test...")
        try:
            if test_name == "latency":
                results["tests"][test_name] = await benchmark.latency_test(num_requests=10)
            elif test_name == "concurrent":
                results["tests"][test_name] = await benchmark.concurrent_test(num_concurrent=5, requests_per_client=3)
            elif test_name == "throughput":
                results["tests"][test_name] = await benchmark.throughput_test(duration_seconds=20)
            elif test_name == "stress":
                results["tests"][test_name] = await benchmark.stress_test(max_concurrent=15)
        except Exception as e:
            results["tests"][test_name] = {"error": str(e)}
    
    return results