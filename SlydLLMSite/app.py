from flask import Flask, render_template, request, jsonify
import json
import os
import subprocess
import requests
import time
import asyncio
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from benchmark import run_benchmark_suite

# Simple Flask app without any proxy configuration
app = Flask(__name__)

# Config file paths
APP_CONFIG_PATH = 'app_config.json'
# Use the systemd service's config location
VLLM_CONFIG_PATH = '/opt/vllm/vllm_config.json'

# HuggingFace token file (separate from config for security)
HF_TOKEN_PATH = os.path.expanduser('~/.huggingface_token')

# Default vLLM configuration (factory settings)
DEFAULT_VLLM_CONFIG = {
    'model': 'HuggingFaceTB/SmolLM3-3B',
    'host': '0.0.0.0',
    'port': 5002,
    'max_num_seqs': 32,
    'gpu_memory_utilization': 0.7,
    'max_model_len': 8192,
    'tensor_parallel_size': 1,
    'dtype': 'auto',
    'trust_remote_code': False
}

def load_app_config():
    """Load application configuration"""
    if os.path.exists(APP_CONFIG_PATH):
        with open(APP_CONFIG_PATH, 'r') as f:
            return json.load(f)
    return {'huggingface_token': ''}

def load_vllm_config():
    """Load vLLM configuration"""
    if os.path.exists(VLLM_CONFIG_PATH):
        with open(VLLM_CONFIG_PATH, 'r') as f:
            return json.load(f)
    return DEFAULT_VLLM_CONFIG.copy()

def save_app_config(config):
    """Save application configuration"""
    with open(APP_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

def save_vllm_config(config):
    """Save vLLM configuration"""
    with open(VLLM_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

def mask_token(token):
    """Mask HuggingFace token for display"""
    if not token:
        return ''
    if len(token) <= 8:
        return token[:2] + '...'
    return token[:8] + '...'

def load_hf_token():
    """Load HuggingFace token from file"""
    if os.path.exists(HF_TOKEN_PATH):
        try:
            with open(HF_TOKEN_PATH, 'r') as f:
                return f.read().strip()
        except:
            pass
    return ''

def save_hf_token(token):
    """Save HuggingFace token to file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(HF_TOKEN_PATH), exist_ok=True)
        with open(HF_TOKEN_PATH, 'w') as f:
            f.write(token)
        # Set restrictive permissions (owner read/write only)
        os.chmod(HF_TOKEN_PATH, 0o600)
        # Also set as environment variable for current session
        os.environ['HUGGINGFACE_TOKEN'] = token
        os.environ['HF_TOKEN'] = token
        return True
    except Exception as e:
        print(f"Error saving HF token: {e}")
        return False

@app.route('/')
def index():
    """Main configuration page"""
    app_config = load_app_config()
    vllm_config = load_vllm_config()

    # Load and mask the HF token for display
    hf_token = load_hf_token()
    masked_token = mask_token(hf_token)

    return render_template('index.html',
                         app_config=app_config,
                         vllm_config=vllm_config,
                         masked_token=masked_token)

@app.route('/check-model', methods=['POST'])
def check_model():
    """Check if HuggingFace model exists"""
    data = request.json
    model_id = data.get('model_id', '')

    if not model_id:
        return jsonify({'valid': False, 'message': 'No model ID provided'})

    try:
        # Check HuggingFace API to see if model exists
        url = f'https://huggingface.co/api/models/{model_id}'
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            return jsonify({'valid': True, 'message': 'Model found and accessible'})
        elif response.status_code == 404:
            return jsonify({'valid': False, 'message': 'Model not found'})
        else:
            return jsonify({'valid': False, 'message': f'HTTP {response.status_code}'})
    except requests.exceptions.RequestException as e:
        return jsonify({'valid': False, 'message': f'Error: {str(e)}'})

@app.route('/save-hf-token', methods=['POST'])
def save_hf_token_endpoint():
    """Save HuggingFace token"""
    data = request.json
    token = data.get('token', '')

    if not token:
        return jsonify({'success': False, 'message': 'No token provided'})
    
    # Don't save if it's the masked version
    if '...' in token and len(token) < 20:
        return jsonify({'success': False, 'message': 'Invalid token format'})

    try:
        if save_hf_token(token):
            return jsonify({
                'success': True, 
                'masked_token': mask_token(token)
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to save token'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/update-config', methods=['POST'])
def update_config():
    """Update vLLM configuration"""
    try:
        # Load existing config to preserve constant fields
        existing_config = load_vllm_config()

        # Update only the editable fields
        new_config = request.json
        existing_config.update(new_config)

        save_vllm_config(existing_config)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/restart-service', methods=['POST'])
def restart_service():
    """Restart the vLLM systemd service"""
    try:
        # Replace 'vllm' with your actual service name
        result = subprocess.run(
            ['systemctl', 'restart', 'vllm'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': result.stderr})
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'message': 'Command timed out'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/service-status')
def service_status():
    """Get the status of the vLLM systemd service"""
    try:
        # Replace 'vllm' with your actual service name
        result = subprocess.run(
            ['systemctl', 'status', 'vllm'],
            capture_output=True,
            text=True,
            timeout=5
        )

        # systemctl status returns 0 for active, 3 for inactive
        active = result.returncode == 0

        return jsonify({
            'active': active,
            'status': 'active' if active else 'inactive',
            'details': result.stdout
        })
    except subprocess.TimeoutExpired:
        return jsonify({'active': False, 'status': 'timeout', 'details': 'Command timed out'})
    except Exception as e:
        return jsonify({'active': False, 'status': 'error', 'details': str(e)})

@app.route('/reset-config', methods=['POST'])
def reset_config():
    """Reset vLLM configuration to factory defaults"""
    try:
        save_vllm_config(DEFAULT_VLLM_CONFIG.copy())
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/get-raw-config')
def get_raw_config():
    """Get the raw vLLM configuration as JSON"""
    try:
        config = load_vllm_config()
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/save-raw-config', methods=['POST'])
def save_raw_config():
    """Save raw vLLM configuration from JSON editor"""
    try:
        data = request.json
        config = data.get('config', {})
        save_vllm_config(config)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/chat-completion', methods=['POST'])
def chat_completion():
    """Send chat completion request to vLLM and return response with metrics"""
    try:
        data = request.json
        user_prompt = data.get('prompt', '')
        
        if not user_prompt:
            return jsonify({'success': False, 'message': 'No prompt provided'})
        
        # Get vLLM config to know the port
        config = load_vllm_config()
        vllm_url = f"http://localhost:{config.get('port', 5002)}/v1/chat/completions"
        
        # Prepare the chat request
        chat_request = {
            "model": config.get('model', 'HuggingFaceTB/SmolLM3-3B'),
            "messages": [
                {"role": "user", "content": user_prompt}
            ],
            "temperature": data.get('temperature', 0.7),
            "max_tokens": data.get('max_tokens', 1000),
            "stream": False
        }
        
        # Track timing
        start_time = time.time()
        
        # Make request to vLLM
        response = requests.post(vllm_url, json=chat_request, timeout=60)
        
        # Calculate latency
        latency = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        if response.status_code != 200:
            return jsonify({
                'success': False, 
                'message': f'vLLM error: {response.status_code}',
                'details': response.text
            })
        
        result = response.json()
        
        # Extract response and metrics
        response_text = result['choices'][0]['message']['content']
        usage = result.get('usage', {})
        
        # Calculate tokens per second
        total_tokens = usage.get('total_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        prompt_tokens = usage.get('prompt_tokens', 0)
        
        # Calculate throughput (tokens per second)
        time_taken_seconds = latency / 1000
        throughput = completion_tokens / time_taken_seconds if time_taken_seconds > 0 else 0
        
        return jsonify({
            'success': True,
            'response': response_text,
            'metrics': {
                'latency_ms': round(latency, 2),
                'throughput_tps': round(throughput, 2),
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': total_tokens,
                'time_seconds': round(time_taken_seconds, 2)
            }
        })
        
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'message': 'Request timed out'})
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'message': 'Cannot connect to vLLM server. Is it running?'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/run-benchmark', methods=['POST'])
def run_benchmark():
    """Run benchmark tests on the vLLM model"""
    try:
        data = request.json
        test_type = data.get('test_type', 'quick')
        
        # Get vLLM config to know the port
        config = load_vllm_config()
        base_url = f"http://localhost:{config.get('port', 5002)}"
        model_name = config.get('model', 'HuggingFaceTB/SmolLM3-3B')
        
        # Define test suites
        if test_type == 'quick':
            tests = ['latency']
        elif test_type == 'standard':
            tests = ['latency', 'concurrent', 'throughput']
        elif test_type == 'full':
            tests = ['latency', 'concurrent', 'throughput', 'stress']
        elif test_type == 'stress':
            tests = ['stress']
        else:
            # Individual test type
            tests = [test_type]
        
        # Run the benchmarks asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(run_benchmark_suite(base_url, model_name, tests))
        loop.close()
        
        return jsonify({'success': True, 'results': results})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)
