from flask import Flask, render_template, request, jsonify, Blueprint
import json
import os
import subprocess
import requests

# Check if running behind proxy with a prefix
PREFIX = os.environ.get('URL_PREFIX', '')

if PREFIX:
    # Create a blueprint with the prefix
    bp = Blueprint('main', __name__, static_folder='static', static_url_path=f'{PREFIX}/static')
    app = Flask(__name__)

    # We'll move routes to the blueprint later, but for now use a simple approach
    class PrefixMiddleware:
        def __init__(self, app, prefix=''):
            self.app = app
            self.prefix = prefix

        def __call__(self, environ, start_response):
            if environ['PATH_INFO'].startswith(self.prefix):
                environ['PATH_INFO'] = environ['PATH_INFO'][len(self.prefix):]
                environ['SCRIPT_NAME'] = self.prefix
            return self.app(environ, start_response)

    app = Flask(__name__)
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix=PREFIX)
else:
    app = Flask(__name__)

# Config file paths
APP_CONFIG_PATH = 'app_config.json'
VLLM_CONFIG_PATH = 'vllm_config.json'
VLLM_CONFIG_DEFAULTS_PATH = 'vllm_config_defaults.json'

# Default vLLM configuration (factory settings)
DEFAULT_VLLM_CONFIG = {
    'model': '',
    'served_model_name': '',
    'host': '0.0.0.0',
    'port': 8001,
    'gpu_memory_utilization': 0.9,
    'max_model_len': 2048,
    'tensor_parallel_size': 1,
    'dtype': 'auto',
    'trust_remote_code': False,
    'max_num_seqs': 256,
    'max_num_batched_tokens': None,
    'quantization': None,
    'kv_cache_dtype': 'auto',
    'enable_prefix_caching': False,
    'enable_chunked_prefill': False,
    'tokenizer': None,
    'revision': None,
    'download_dir': None,
    'load_format': 'auto'
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

@app.route('/')
def index():
    """Main configuration page"""
    app_config = load_app_config()
    vllm_config = load_vllm_config()

    # Mask the HF token for display
    masked_token = mask_token(app_config.get('huggingface_token', ''))

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

@app.route('/save-token', methods=['POST'])
def save_token():
    """Save HuggingFace token"""
    data = request.json
    token = data.get('token', '')

    if not token:
        return jsonify({'success': False, 'message': 'No token provided'})

    try:
        app_config = load_app_config()
        app_config['huggingface_token'] = token
        save_app_config(app_config)
        return jsonify({'success': True})
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)
