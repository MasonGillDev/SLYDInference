// Check if HuggingFace model is valid
async function checkModel() {
    const modelId = document.getElementById('model-id').value;
    const statusDiv = document.getElementById('model-status');

    if (!modelId) {
        showStatus(statusDiv, 'Please enter a model ID', 'error');
        return;
    }

    // Show loading state
    statusDiv.textContent = 'Checking model...';
    statusDiv.className = 'status-message';
    statusDiv.style.display = 'block';

    try {
        const response = await fetch(`${window.API_BASE}/check-model`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ model_id: modelId })
        });

        const data = await response.json();

        if (data.valid) {
            showStatus(statusDiv, '✓ Model is valid and accessible', 'success');
        } else {
            showStatus(statusDiv, '✗ ' + (data.message || 'Model not found'), 'error');
        }
    } catch (error) {
        showStatus(statusDiv, '✗ Error checking model: ' + error.message, 'error');
    }
}

// Save vLLM configuration
async function saveConfig() {
    const config = {
        model: document.getElementById('model-id').value,
        host: document.getElementById('host').value,
        port: parseInt(document.getElementById('port').value),
        max_num_seqs: parseInt(document.getElementById('max-num-seqs').value),
        gpu_memory_utilization: parseFloat(document.getElementById('gpu-memory').value),
        max_model_len: parseInt(document.getElementById('max-model-len').value),
        tensor_parallel_size: parseInt(document.getElementById('tensor-parallel').value),
        dtype: document.getElementById('dtype').value,
        trust_remote_code: document.getElementById('trust-remote-code').checked
    };

    try {
        const response = await fetch(`${window.API_BASE}/update-config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(config)
        });

        const data = await response.json();

        if (data.success) {
            alert('✓ Configuration saved successfully');
        } else {
            alert('✗ Error saving configuration: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        alert('✗ Error saving configuration: ' + error.message);
    }
}

// Restart vLLM service
async function restartService() {
    if (!confirm('Are you sure you want to restart the vLLM service?')) {
        return;
    }

    const statusDiv = document.getElementById('service-status');
    statusDiv.textContent = 'Restarting service...';
    statusDiv.className = 'status-message';
    statusDiv.style.display = 'block';

    try {
        const response = await fetch(`${window.API_BASE}/restart-service`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showStatus(statusDiv, '✓ Service restarted successfully', 'success');
            setTimeout(() => {
                checkServiceStatus();
            }, 3000);
        } else {
            showStatus(statusDiv, '✗ Error restarting service: ' + (data.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        showStatus(statusDiv, '✗ Error restarting service: ' + error.message, 'error');
    }
}

// Check service status
async function checkServiceStatus() {
    const statusDiv = document.getElementById('service-status');
    statusDiv.textContent = 'Checking service status...';
    statusDiv.className = 'status-message';
    statusDiv.style.display = 'block';

    try {
        const response = await fetch(`${window.API_BASE}/service-status`);
        const data = await response.json();

        if (data.active) {
            showStatus(statusDiv, '✓ Service is running', 'success');
            
            // Also check if the API is responding
            try {
                const apiResponse = await fetch(`http://${window.location.hostname}:${document.getElementById('port').value}/v1/models`);
                if (apiResponse.ok) {
                    statusDiv.innerHTML += '<br>✓ API is responding on port ' + document.getElementById('port').value;
                }
            } catch (e) {
                statusDiv.innerHTML += '<br>⚠ API not responding (service may be starting)';
            }
        } else {
            showStatus(statusDiv, '✗ Service is not running', 'error');
        }
    } catch (error) {
        showStatus(statusDiv, '✗ Error checking status: ' + error.message, 'error');
    }
}

// Reset to default configuration
async function resetToDefaults() {
    if (!confirm('Are you sure you want to reset to default configuration?')) {
        return;
    }

    try {
        const response = await fetch(`${window.API_BASE}/reset-config`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            alert('✓ Configuration reset to defaults');
            location.reload();
        } else {
            alert('✗ Error resetting configuration: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        alert('✗ Error resetting configuration: ' + error.message);
    }
}

// Toggle raw JSON editor
function toggleRawEditor() {
    const editor = document.getElementById('raw-editor');
    const toggleText = document.getElementById('toggle-text');
    
    if (editor.style.display === 'none') {
        // Load current config into editor
        loadRawConfig();
        editor.style.display = 'block';
        toggleText.textContent = 'Hide Raw JSON Editor';
    } else {
        editor.style.display = 'none';
        toggleText.textContent = 'Show Raw JSON Editor';
    }
}

// Load raw configuration
async function loadRawConfig() {
    try {
        const response = await fetch(`${window.API_BASE}/get-raw-config`);
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('raw-config-textarea').value = JSON.stringify(data.config, null, 2);
        }
    } catch (error) {
        console.error('Error loading raw config:', error);
    }
}

// Save raw configuration
async function saveRawConfig() {
    const statusDiv = document.getElementById('raw-editor-status');
    const rawConfig = document.getElementById('raw-config-textarea').value;
    
    try {
        // Validate JSON
        const config = JSON.parse(rawConfig);
        
        const response = await fetch(`${window.API_BASE}/save-raw-config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ config: config })
        });

        const data = await response.json();

        if (data.success) {
            showStatus(statusDiv, '✓ Raw configuration saved successfully', 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showStatus(statusDiv, '✗ Error saving configuration: ' + (data.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        if (error instanceof SyntaxError) {
            showStatus(statusDiv, '✗ Invalid JSON format', 'error');
        } else {
            showStatus(statusDiv, '✗ Error saving configuration: ' + error.message, 'error');
        }
    }
}

// Cancel raw edit
function cancelRawEdit() {
    document.getElementById('raw-editor').style.display = 'none';
    document.getElementById('toggle-text').textContent = 'Show Raw JSON Editor';
}

// Utility function to show status messages
function showStatus(element, message, type) {
    element.textContent = message;
    element.className = 'status-message ' + type;
    element.style.display = 'block';
    
    // Auto-hide after 5 seconds for non-error messages
    if (type !== 'error') {
        setTimeout(() => {
            element.style.display = 'none';
        }, 5000);
    }
}

// Check service status on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check service status automatically on load
    checkServiceStatus();
});