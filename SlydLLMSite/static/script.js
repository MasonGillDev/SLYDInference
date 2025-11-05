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
    const maxBatchedTokens = document.getElementById('max-num-batched-tokens').value;
    const quantization = document.getElementById('quantization').value;
    const tokenizer = document.getElementById('tokenizer').value;
    const revision = document.getElementById('revision').value;
    const downloadDir = document.getElementById('download-dir').value;

    const config = {
        model: document.getElementById('model-id').value,
        gpu_memory_utilization: parseFloat(document.getElementById('gpu-memory').value),
        max_model_len: parseInt(document.getElementById('max-model-len').value),
        tensor_parallel_size: parseInt(document.getElementById('tensor-parallel').value),
        dtype: document.getElementById('dtype').value,
        trust_remote_code: document.getElementById('trust-remote-code').checked,
        max_num_seqs: parseInt(document.getElementById('max-num-seqs').value),
        kv_cache_dtype: document.getElementById('kv-cache-dtype').value,
        enable_prefix_caching: document.getElementById('enable-prefix-caching').checked,
        enable_chunked_prefill: document.getElementById('enable-chunked-prefill').checked,
        load_format: document.getElementById('load-format').value
    };

    // Add optional fields only if they have values
    if (maxBatchedTokens) {
        config.max_num_batched_tokens = parseInt(maxBatchedTokens);
    }
    if (quantization) {
        config.quantization = quantization;
    }
    if (tokenizer) {
        config.tokenizer = tokenizer;
    }
    if (revision) {
        config.revision = revision;
    }
    if (downloadDir) {
        config.download_dir = downloadDir;
    }

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

// Save HuggingFace token
async function saveToken() {
    const token = document.getElementById('hf-token').value;

    if (!token) {
        alert('Please enter a HuggingFace token');
        return;
    }

    try {
        const response = await fetch(`${window.API_BASE}/save-token`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ token: token })
        });

        const data = await response.json();

        if (data.success) {
            alert('✓ Token saved successfully');
            location.reload();
        } else {
            alert('✗ Error saving token: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        alert('✗ Error saving token: ' + error.message);
    }
}

// Edit HuggingFace token
function editToken() {
    if (confirm('Are you sure you want to edit the HuggingFace token?')) {
        location.reload();
    }
}

// Reset configuration to defaults
async function resetToDefaults() {
    if (!confirm('Are you sure you want to reset all settings to factory defaults? This cannot be undone.')) {
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

// Restart vLLM service
async function restartService() {
    if (!confirm('Are you sure you want to restart the vLLM service?')) {
        return;
    }

    try {
        const response = await fetch(`${window.API_BASE}/restart-service`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            alert('✓ Service restart initiated');
            checkServiceStatus();
        } else {
            alert('✗ Error restarting service: ' + (data.message || 'Unknown error'));
        }
    } catch (error) {
        alert('✗ Error restarting service: ' + error.message);
    }
}

// Check service status
async function checkServiceStatus() {
    const statusCard = document.getElementById('service-status');
    statusCard.textContent = 'Checking service status...';
    statusCard.className = 'status-card show';

    try {
        const response = await fetch(`${window.API_BASE}/service-status`);
        const data = await response.json();

        let statusHTML = `
            <h3 style="margin-bottom: 0.75rem; font-size: 1rem; font-weight: 600;">Service Status</h3>
            <div style="display: grid; gap: 0.5rem; font-size: 0.875rem;">
                <div><strong>Status:</strong> <span style="color: ${data.active ? '#10b981' : '#ef4444'}">${data.status || 'Unknown'}</span></div>
                <div><strong>Running:</strong> ${data.active ? '✓ Yes' : '✗ No'}</div>
            </div>
        `;

        if (data.details) {
            statusHTML += `<pre style="margin-top: 0.75rem; padding: 0.75rem; background-color: #f8fafc; border-radius: 0.375rem; font-size: 0.75rem; overflow-x: auto;">${data.details}</pre>`;
        }

        statusCard.innerHTML = statusHTML;
    } catch (error) {
        statusCard.innerHTML = `<div style="color: #ef4444;">Error checking status: ${error.message}</div>`;
    }
}

// Helper function to show status messages
function showStatus(element, message, type) {
    element.textContent = message;
    element.className = `status-message ${type}`;
    element.style.display = 'block';
}

// Toggle raw JSON editor visibility
function toggleRawEditor() {
    const editor = document.getElementById('raw-editor');
    const toggleText = document.getElementById('toggle-text');
    const isVisible = editor.style.display !== 'none';

    if (isVisible) {
        // Hide editor
        editor.style.display = 'none';
        toggleText.textContent = 'Show Raw JSON Editor';
    } else {
        // Show editor and load current config
        loadRawConfig();
        editor.style.display = 'block';
        toggleText.textContent = 'Hide Raw JSON Editor';
        // Scroll to editor
        editor.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Load current configuration into raw editor
async function loadRawConfig() {
    try {
        const response = await fetch(`${window.API_BASE}/get-raw-config`);
        const data = await response.json();

        if (data.success) {
            const textarea = document.getElementById('raw-config-textarea');
            textarea.value = JSON.stringify(data.config, null, 2);
        }
    } catch (error) {
        console.error('Error loading raw config:', error);
    }
}

// Save raw JSON configuration
async function saveRawConfig() {
    const textarea = document.getElementById('raw-config-textarea');
    const statusDiv = document.getElementById('raw-editor-status');

    try {
        // Parse JSON to validate it
        const config = JSON.parse(textarea.value);

        // Send to server
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
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            showStatus(statusDiv, '✗ Error saving: ' + (data.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        if (error instanceof SyntaxError) {
            showStatus(statusDiv, '✗ Invalid JSON syntax. Please fix errors before saving.', 'error');
        } else {
            showStatus(statusDiv, '✗ Error: ' + error.message, 'error');
        }
    }
}

// Cancel raw editing and hide editor
function cancelRawEdit() {
    const editor = document.getElementById('raw-editor');
    const toggleText = document.getElementById('toggle-text');
    const statusDiv = document.getElementById('raw-editor-status');

    editor.style.display = 'none';
    toggleText.textContent = 'Show Raw JSON Editor';
    statusDiv.style.display = 'none';
}
