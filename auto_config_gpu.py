#!/usr/bin/env python3
"""
Auto-configure vLLM based on GPU hardware and model size.

Detects GPU VRAM via torch.cuda (preferred) or nvidia-smi (fallback),
estimates model memory from a local lookup table, and writes optimal
gpu_memory_utilization, max_model_len, tensor_parallel_size, and
quantization into vllm_config.json.

Skips any key the user has intentionally customized (differs from defaults).

Usage:
    python3 auto_config_gpu.py --config vllm_config.json --defaults default_vllm_config.json
    python3 auto_config_gpu.py --dry-run
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys

LOG_FILE = "/var/log/auto_config_gpu.log"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

log = logging.getLogger("auto_config_gpu")


def setup_logging(dry_run: bool = False):
    log.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(fmt)
    log.addHandler(stdout_handler)

    if not dry_run:
        try:
            file_handler = logging.FileHandler(LOG_FILE)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(fmt)
            log.addHandler(file_handler)
        except PermissionError:
            log.warning("Cannot write to %s — file logging disabled", LOG_FILE)


# ---------------------------------------------------------------------------
# GPU Detection
# ---------------------------------------------------------------------------

def detect_gpu_torch():
    """Detect GPU info via torch.cuda."""
    try:
        import torch
        if not torch.cuda.is_available():
            return None
        count = torch.cuda.device_count()
        name = torch.cuda.get_device_name(0)
        vram_bytes = torch.cuda.get_device_properties(0).total_mem
        vram_gb = vram_bytes / (1024 ** 3)
        return {"gpu_count": count, "gpu_name": name, "vram_gb": round(vram_gb, 2)}
    except Exception as exc:
        log.debug("torch detection failed: %s", exc)
        return None


def detect_gpu_nvidia_smi():
    """Detect GPU info via nvidia-smi (fallback)."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,count",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None
        lines = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        if not lines:
            return None
        parts = lines[0].split(", ")
        name = parts[0]
        vram_mb = float(parts[1])
        count = len(lines)
        return {"gpu_count": count, "gpu_name": name, "vram_gb": round(vram_mb / 1024, 2)}
    except Exception as exc:
        log.debug("nvidia-smi detection failed: %s", exc)
        return None


def detect_gpu():
    """Return GPU info dict or None."""
    info = detect_gpu_torch()
    if info:
        log.info("GPU detected via torch: %s", info)
        return info
    info = detect_gpu_nvidia_smi()
    if info:
        log.info("GPU detected via nvidia-smi: %s", info)
        return info
    log.warning("No GPU detected")
    return None


# ---------------------------------------------------------------------------
# Model Lookup Table
# ---------------------------------------------------------------------------

# Maps (param_class, quant) -> {weight_gb, layers, kv_heads, head_dim, max_context}
# quant key: "fp16", "awq", "gptq", "int8"
MODEL_LOOKUP = {
    # --- Llama 3 / 3.1 family ---
    ("70B", "fp16"):  {"weight_gb": 140.0, "layers": 80, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("70B", "awq"):   {"weight_gb": 35.0,  "layers": 80, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("70B", "gptq"):  {"weight_gb": 35.0,  "layers": 80, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("70B", "int8"):  {"weight_gb": 70.0,  "layers": 80, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("8B", "fp16"):   {"weight_gb": 16.0,  "layers": 32, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("8B", "awq"):    {"weight_gb": 4.0,   "layers": 32, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("8B", "gptq"):   {"weight_gb": 4.0,   "layers": 32, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("8B", "int8"):   {"weight_gb": 8.0,   "layers": 32, "kv_heads": 8, "head_dim": 128, "max_context": 131072},

    # --- Llama 3.2 small ---
    ("3B", "fp16"):   {"weight_gb": 6.0,   "layers": 28, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("3B", "awq"):    {"weight_gb": 1.5,   "layers": 28, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("1B", "fp16"):   {"weight_gb": 2.0,   "layers": 16, "kv_heads": 8, "head_dim": 64,  "max_context": 131072},

    # --- Llama 4 ---
    ("109B", "fp16"): {"weight_gb": 218.0, "layers": 48, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("109B", "awq"):  {"weight_gb": 55.0,  "layers": 48, "kv_heads": 8, "head_dim": 128, "max_context": 131072},

    # --- Qwen 2.5 family ---
    ("72B", "fp16"):  {"weight_gb": 144.0, "layers": 80, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("72B", "awq"):   {"weight_gb": 36.0,  "layers": 80, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("72B", "gptq"):  {"weight_gb": 36.0,  "layers": 80, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("32B", "fp16"):  {"weight_gb": 64.0,  "layers": 64, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("32B", "awq"):   {"weight_gb": 16.0,  "layers": 64, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("14B", "fp16"):  {"weight_gb": 28.0,  "layers": 48, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("14B", "awq"):   {"weight_gb": 7.0,   "layers": 48, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("7B", "fp16"):   {"weight_gb": 14.0,  "layers": 32, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("7B", "awq"):    {"weight_gb": 3.5,   "layers": 32, "kv_heads": 8, "head_dim": 128, "max_context": 131072},

    # --- Mistral / Mixtral ---
    ("22B", "fp16"):  {"weight_gb": 44.0,  "layers": 56, "kv_heads": 8, "head_dim": 128, "max_context": 32768},
    ("22B", "awq"):   {"weight_gb": 11.0,  "layers": 56, "kv_heads": 8, "head_dim": 128, "max_context": 32768},
    ("12B", "fp16"):  {"weight_gb": 24.0,  "layers": 40, "kv_heads": 8, "head_dim": 128, "max_context": 131072},
    ("12B", "awq"):   {"weight_gb": 6.0,   "layers": 40, "kv_heads": 8, "head_dim": 128, "max_context": 131072},

    # --- Phi-3 / Phi-4 ---
    ("4B", "fp16"):   {"weight_gb": 8.0,   "layers": 40, "kv_heads": 8, "head_dim": 96,  "max_context": 16384},
    ("4B", "awq"):    {"weight_gb": 2.0,   "layers": 40, "kv_heads": 8, "head_dim": 96,  "max_context": 16384},

    # --- Gemma 2 ---
    ("27B", "fp16"):  {"weight_gb": 54.0,  "layers": 46, "kv_heads": 16, "head_dim": 128, "max_context": 8192},
    ("27B", "awq"):   {"weight_gb": 13.5,  "layers": 46, "kv_heads": 16, "head_dim": 128, "max_context": 8192},
    ("9B", "fp16"):   {"weight_gb": 18.0,  "layers": 42, "kv_heads": 8, "head_dim": 128,  "max_context": 8192},
    ("9B", "awq"):    {"weight_gb": 4.5,   "layers": 42, "kv_heads": 8, "head_dim": 128,  "max_context": 8192},
    ("2B", "fp16"):   {"weight_gb": 4.0,   "layers": 26, "kv_heads": 4, "head_dim": 128,  "max_context": 8192},

    # --- DeepSeek ---
    ("67B", "fp16"):  {"weight_gb": 134.0, "layers": 95, "kv_heads": 8, "head_dim": 128, "max_context": 16384},
    ("67B", "awq"):   {"weight_gb": 33.5,  "layers": 95, "kv_heads": 8, "head_dim": 128, "max_context": 16384},

    # --- SmolLM ---
    ("0.1B", "fp16"): {"weight_gb": 0.5,   "layers": 12, "kv_heads": 8, "head_dim": 64, "max_context": 8192},
    ("0.3B", "fp16"): {"weight_gb": 1.0,   "layers": 16, "kv_heads": 8, "head_dim": 64, "max_context": 8192},
    ("1.7B", "fp16"): {"weight_gb": 3.4,   "layers": 24, "kv_heads": 8, "head_dim": 64, "max_context": 8192},
}


# ---------------------------------------------------------------------------
# Model Name Parsing
# ---------------------------------------------------------------------------

def parse_param_count(model_name: str) -> str | None:
    """Extract parameter count class like '70B', '8B', '3B' from model name."""
    upper = model_name.upper()
    # Match patterns like 70B, 8B, 3B, 1.7B, 0.5B etc.
    m = re.search(r"[\-_/](\d+(?:\.\d+)?)\s*B(?:[\-_/\s]|$)", upper)
    if m:
        raw = m.group(1)
        # Normalise: strip trailing .0
        if "." in raw and raw.endswith("0") and raw.split(".")[1] == "0":
            return raw.split(".")[0] + "B"
        return raw + "B"
    return None


def parse_quantization(model_name: str) -> str:
    """Detect quantization from model name. Returns 'fp16' if none found."""
    upper = model_name.upper()
    if "AWQ" in upper or "INT4" in upper:
        return "awq"
    if "GPTQ" in upper:
        return "gptq"
    if "INT8" in upper:
        return "int8"
    return "fp16"


def estimate_model_info(model_name: str) -> dict:
    """
    Return model info dict with keys:
      weight_gb, layers, kv_heads, head_dim, max_context, quant, param_class
    """
    param_class = parse_param_count(model_name)
    quant = parse_quantization(model_name)

    log.info("Parsed model name '%s' -> param_class=%s, quant=%s", model_name, param_class, quant)

    if param_class and (param_class, quant) in MODEL_LOOKUP:
        info = dict(MODEL_LOOKUP[(param_class, quant)])
        info["quant"] = quant
        info["param_class"] = param_class
        log.info("Lookup table hit: %s", info)
        return info

    # Fallback: estimate from param count
    if param_class:
        try:
            params_b = float(param_class.rstrip("B"))
        except ValueError:
            params_b = 7.0  # safe default
    else:
        params_b = 7.0
        param_class = "7B"
        log.warning("Could not parse param count from '%s', assuming 7B", model_name)

    # Bytes per param
    bpp = {"fp16": 2.0, "awq": 0.5, "gptq": 0.5, "int8": 1.0}.get(quant, 2.0)
    weight_gb = params_b * bpp

    # Conservative architecture defaults scaled by param count
    if params_b >= 60:
        layers, kv_heads, head_dim = 80, 8, 128
    elif params_b >= 25:
        layers, kv_heads, head_dim = 56, 8, 128
    elif params_b >= 10:
        layers, kv_heads, head_dim = 40, 8, 128
    elif params_b >= 5:
        layers, kv_heads, head_dim = 32, 8, 128
    elif params_b >= 2:
        layers, kv_heads, head_dim = 24, 8, 64
    else:
        layers, kv_heads, head_dim = 16, 8, 64

    max_context = 8192  # conservative default for unknown models

    info = {
        "weight_gb": round(weight_gb, 2),
        "layers": layers,
        "kv_heads": kv_heads,
        "head_dim": head_dim,
        "max_context": max_context,
        "quant": quant,
        "param_class": param_class,
    }
    log.info("Fallback estimate: %s", info)
    return info


# ---------------------------------------------------------------------------
# Config Calculation
# ---------------------------------------------------------------------------

def calculate_config(gpu_info: dict, model_info: dict) -> dict:
    """
    Calculate optimal vLLM config values.

    Returns dict with keys:
      gpu_memory_utilization, max_model_len, tensor_parallel_size,
      quantization, max_num_seqs
    """
    gpu_count = gpu_info["gpu_count"]
    per_gpu_vram = gpu_info["vram_gb"]

    tp_size = gpu_count

    # Per-GPU model memory: (weight * 1.10 activation overhead + 0.5 GB fixed) / tp
    estimated_weight = model_info["weight_gb"]
    per_gpu_model_gb = (estimated_weight * 1.10 + 0.5) / tp_size

    # GPU memory utilization: enough for model + 1 GB KV cache headroom, capped 0.70..0.95
    utilization = (per_gpu_model_gb + 1.0) / per_gpu_vram
    utilization = max(0.70, min(0.95, utilization))
    utilization = round(utilization, 2)

    # Verify at least 1.5 GB headroom remains
    allocated = per_gpu_vram * utilization
    headroom = per_gpu_vram - allocated
    if headroom < 1.5:
        utilization = round((per_gpu_vram - 1.5) / per_gpu_vram, 2)
        utilization = max(0.70, min(0.95, utilization))
        allocated = per_gpu_vram * utilization

    log.info(
        "Per-GPU: model=%.1f GB, allocated=%.1f GB (util=%.2f), headroom=%.1f GB",
        per_gpu_model_gb, allocated, utilization, per_gpu_vram - allocated,
    )

    # KV cache memory available per GPU
    kv_available_gb = allocated - per_gpu_model_gb
    if kv_available_gb < 0.5:
        log.warning("Very little KV cache space (%.2f GB) — model may be too large for this GPU", kv_available_gb)
        kv_available_gb = 0.5

    # Per-token KV cache size in bytes:
    # num_layers * 2 (K+V) * num_kv_heads * head_dim * 2 (fp16 bytes)
    layers = model_info["layers"]
    kv_heads = model_info["kv_heads"]
    head_dim = model_info["head_dim"]
    # For tensor parallelism, KV heads are split across GPUs
    kv_heads_per_gpu = max(1, kv_heads // tp_size) if kv_heads >= tp_size else kv_heads
    kv_per_token_bytes = layers * 2 * kv_heads_per_gpu * head_dim * 2

    log.info(
        "KV cache: layers=%d, kv_heads_per_gpu=%d, head_dim=%d -> %.0f bytes/token",
        layers, kv_heads_per_gpu, head_dim, kv_per_token_bytes,
    )

    # max_model_len from available KV cache
    kv_available_bytes = kv_available_gb * (1024 ** 3)
    max_model_len = int(kv_available_bytes / kv_per_token_bytes)

    # Cap at model's native max context
    native_max = model_info.get("max_context", 8192)
    if max_model_len > native_max:
        max_model_len = native_max

    # Round down to nearest 256
    max_model_len = (max_model_len // 256) * 256

    # Minimum viable context length
    if max_model_len < 512:
        max_model_len = 512
        log.warning("KV cache very tight — forcing max_model_len=512")

    log.info("max_model_len = %d (native max = %d)", max_model_len, native_max)

    # Quantization
    quant = model_info["quant"]
    quant_value = quant if quant != "fp16" else None

    # max_num_seqs: reduce if VRAM is very tight
    max_num_seqs = 32
    if kv_available_gb < 2.0:
        max_num_seqs = 8
        log.info("Tight VRAM — reducing max_num_seqs to %d", max_num_seqs)
    elif kv_available_gb < 4.0:
        max_num_seqs = 16
        log.info("Moderate VRAM — reducing max_num_seqs to %d", max_num_seqs)

    result = {
        "gpu_memory_utilization": utilization,
        "max_model_len": max_model_len,
        "tensor_parallel_size": tp_size,
        "quantization": quant_value,
        "max_num_seqs": max_num_seqs,
    }

    log.info("Calculated config: %s", result)
    return result


# ---------------------------------------------------------------------------
# Config Application
# ---------------------------------------------------------------------------

AUTO_TUNE_KEYS = {
    "gpu_memory_utilization",
    "max_model_len",
    "tensor_parallel_size",
    "quantization",
    "max_num_seqs",
}


def load_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def save_json(path: str, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def apply_config(config_path: str, defaults_path: str, new_values: dict, dry_run: bool = False):
    """
    Apply new_values to config, but skip any key the user has customized
    (i.e. where config[key] != defaults[key]).
    """
    config = load_json(config_path)
    defaults = load_json(defaults_path)

    for key, new_val in new_values.items():
        if key not in AUTO_TUNE_KEYS:
            continue

        current = config.get(key)
        default = defaults.get(key)

        # If user has customized this key, skip it
        if current != default:
            log.info("Skipping '%s': user-customized (current=%s, default=%s)", key, current, default)
            continue

        if current == new_val:
            log.debug("Skipping '%s': already set to %s", key, new_val)
            continue

        log.info("Setting '%s': %s -> %s", key, current, new_val)
        config[key] = new_val

    if dry_run:
        log.info("DRY RUN — would write config:\n%s", json.dumps(config, indent=2))
    else:
        save_json(config_path, config)
        log.info("Config written to %s", config_path)

    return config


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Auto-configure vLLM based on GPU hardware and model size"
    )
    parser.add_argument(
        "--config", default="vllm_config.json",
        help="Path to vllm_config.json (default: vllm_config.json)",
    )
    parser.add_argument(
        "--defaults", default="default_vllm_config.json",
        help="Path to default_vllm_config.json (default: default_vllm_config.json)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print calculated config without writing",
    )
    args = parser.parse_args()

    setup_logging(dry_run=args.dry_run)

    log.info("=== auto_config_gpu starting ===")

    # 1. Detect GPU
    gpu_info = detect_gpu()
    if gpu_info is None:
        log.warning("No GPU detected — skipping auto-configuration")
        sys.exit(0)

    # 2. Read model name from config
    if not os.path.exists(args.config):
        log.error("Config file not found: %s", args.config)
        sys.exit(1)
    if not os.path.exists(args.defaults):
        log.error("Defaults file not found: %s", args.defaults)
        sys.exit(1)

    config = load_json(args.config)
    model_name = config.get("model", "")
    if not model_name:
        log.warning("No model specified in config — skipping auto-configuration")
        sys.exit(0)

    log.info("Model: %s", model_name)

    # 3. Estimate model size
    model_info = estimate_model_info(model_name)

    # 4. Calculate optimal config
    new_values = calculate_config(gpu_info, model_info)

    # 5. Apply config
    apply_config(args.config, args.defaults, new_values, dry_run=args.dry_run)

    log.info("=== auto_config_gpu complete ===")


if __name__ == "__main__":
    main()
