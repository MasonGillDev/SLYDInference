#!/usr/bin/env python3
import json
import subprocess
import sys
import argparse
from pathlib import Path
import importlib.util

def load_config(config_path):
    """Load vLLM configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)

def build_vllm_command(config):
    """Build vLLM server command from config."""
    cmd = ["python3", "-m", "vllm.entrypoints.openai.api_server"]
    
    # Add model if specified
    if config.get("model"):
        cmd.extend(["--model", config["model"]])
    
    # Add served model name if specified
    if config.get("served_model_name"):
        cmd.extend(["--served-model-name", config["served_model_name"]])
    
    # Add host and port
    cmd.extend(["--host", str(config.get("host", "0.0.0.0"))])
    cmd.extend(["--port", str(config.get("port", 5002))])
    
    # Add GPU memory utilization
    if config.get("gpu_memory_utilization"):
        cmd.extend(["--gpu-memory-utilization", str(config["gpu_memory_utilization"])])
    
    # Add max model length
    if config.get("max_model_len"):
        cmd.extend(["--max-model-len", str(config["max_model_len"])])
    
    # Add tensor parallel size
    if config.get("tensor_parallel_size"):
        cmd.extend(["--tensor-parallel-size", str(config["tensor_parallel_size"])])
    
    # Add dtype
    if config.get("dtype") and config["dtype"] != "auto":
        cmd.extend(["--dtype", config["dtype"]])
    
    # Add trust remote code
    if config.get("trust_remote_code"):
        cmd.append("--trust-remote-code")
    
    # Add max num seqs
    if config.get("max_num_seqs"):
        cmd.extend(["--max-num-seqs", str(config["max_num_seqs"])])
    
    # Add max num batched tokens
    if config.get("max_num_batched_tokens"):
        cmd.extend(["--max-num-batched-tokens", str(config["max_num_batched_tokens"])])
    
    # Add quantization
    if config.get("quantization"):
        cmd.extend(["--quantization", config["quantization"]])
    
    # Add kv cache dtype
    if config.get("kv_cache_dtype") and config["kv_cache_dtype"] != "auto":
        cmd.extend(["--kv-cache-dtype", config["kv_cache_dtype"]])
    
    # Add enable prefix caching
    if config.get("enable_prefix_caching"):
        cmd.append("--enable-prefix-caching")
    
    # Add enable chunked prefill
    if config.get("enable_chunked_prefill"):
        cmd.append("--enable-chunked-prefill")
    
    # Add tokenizer if specified
    if config.get("tokenizer") and config["tokenizer"] not in [None, "None", "null"]:
        cmd.extend(["--tokenizer", config["tokenizer"]])
    
    # Add revision if specified
    if config.get("revision") and config["revision"] not in [None, "None", "null"]:
        cmd.extend(["--revision", config["revision"]])
    
    # Add download dir if specified
    if config.get("download_dir") and config["download_dir"] not in [None, "None", "null"]:
        cmd.extend(["--download-dir", config["download_dir"]])
    
    # Add load format
    if config.get("load_format") and config["load_format"] != "auto":
        cmd.extend(["--load-format", config["load_format"]])
    
    return cmd

def check_vllm_installed():
    """Check if vLLM is installed."""
    vllm_spec = importlib.util.find_spec("vllm")
    return vllm_spec is not None

def main():
    parser = argparse.ArgumentParser(description='Launch vLLM server from config file')
    parser.add_argument('--config', type=str, default='vllm_config_port5002.json',
                        help='Path to vLLM config JSON file')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print command without executing')
    args = parser.parse_args()
    
    # Check if vLLM is installed
    if not check_vllm_installed():
        print("Error: vLLM is not installed.")
        print("Install it with: pip install vllm")
        print("Or for GPU support: pip install vllm[cuda12]")
        sys.exit(1)
    
    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)
    
    try:
        config = load_config(config_path)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)
    
    # Check if model is specified
    if not config.get("model"):
        print("Error: 'model' must be specified in the config file")
        sys.exit(1)
    
    # Build command
    cmd = build_vllm_command(config)
    
    # Print command for debugging
    print(f"Starting vLLM server with command:")
    print(" ".join(cmd))
    
    if args.dry_run:
        print("\nDry run mode - command not executed")
        sys.exit(0)
    
    # Execute command
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error running vLLM server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()