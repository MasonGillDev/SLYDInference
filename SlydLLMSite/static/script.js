// Check model function is no longer needed since model is read-only

// Save vLLM configuration
async function saveConfig() {
    const config = {
        // Model is read-only, get from original config
        host: document.getElementById('host').value,
        port: parseInt(document.getElementById('port').value),
        max_num_seqs: parseInt(document.getElementById('max-num-seqs').value),
        gpu_memory_utilization: parseFloat(document.getElementById('gpu-memory').value),
        max_model_len: parseInt(document.getElementById('max-model-len').value),
        tensor_parallel_size: parseInt(document.getElementById('tensor-parallel').value),
        dtype: document.getElementById('dtype').value,
        trust_remote_code: document.getElementById('trust-remote-code').checked,
        
        // Advanced Options
        quantization: document.getElementById('quantization').value === 'null' ? null : document.getElementById('quantization').value,
        seed: parseInt(document.getElementById('seed').value),
        swap_space: parseInt(document.getElementById('swap-space').value),
        block_size: parseInt(document.getElementById('block-size').value),
        enable_prefix_caching: document.getElementById('enable-prefix-caching').checked,
        enable_chunked_prefill: document.getElementById('enable-chunked-prefill').checked,
        
        // Batching & Scheduling
        max_num_batched_tokens: document.getElementById('max-num-batched-tokens').value ? 
            parseInt(document.getElementById('max-num-batched-tokens').value) : null,
        
        // Tokenizer Settings
        tokenizer: document.getElementById('tokenizer').value || null,
        
        // API Settings
        chat_template: document.getElementById('chat-template').value || null,
        response_role: document.getElementById('response-role').value,
        served_model_name: document.getElementById('served-model-name').value || null,
        disable_log_stats: document.getElementById('disable-log-stats').checked,
        
        // LoRA Settings
        enable_lora: document.getElementById('enable-lora').checked,
        max_loras: parseInt(document.getElementById('max-loras').value),
        max_lora_rank: parseInt(document.getElementById('max-lora-rank').value),
        lora_dtype: document.getElementById('lora-dtype').value,
        max_cpu_loras: document.getElementById('max-cpu-loras').value ? 
            parseInt(document.getElementById('max-cpu-loras').value) : null
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
            
            // Also check if the API is responding through the proxy
            // Since nginx routes /v1/* directly to vLLM, we need to use the full URL
            try {
                const currentHost = window.location.protocol + '//' + window.location.host;
                const apiResponse = await fetch(`${currentHost}/v1/models`);
                if (apiResponse.ok) {
                    statusDiv.innerHTML += '<br>✓ API is responding';
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

// Toggle advanced options visibility
function toggleAdvancedOptions() {
    const advancedDiv = document.getElementById('advanced-options');
    const arrow = document.getElementById('advanced-arrow');
    
    if (advancedDiv.style.display === 'none') {
        advancedDiv.style.display = 'block';
        arrow.style.transform = 'rotate(90deg)';
    } else {
        advancedDiv.style.display = 'none';
        arrow.style.transform = 'rotate(0deg)';
    }
}

// Toggle LoRA options visibility
function toggleLoraOptions() {
    const loraOptionsDiv = document.getElementById('lora-options');
    const enableLora = document.getElementById('enable-lora').checked;
    
    if (enableLora) {
        loraOptionsDiv.style.display = 'block';
    } else {
        loraOptionsDiv.style.display = 'none';
    }
}

// Send chat message to vLLM
async function sendChatMessage() {
    const prompt = document.getElementById('chat-prompt').value.trim();
    
    if (!prompt) {
        alert('Please enter a prompt');
        return;
    }
    
    // Hide previous results and errors
    document.getElementById('chat-response').style.display = 'none';
    document.getElementById('chat-metrics').style.display = 'none';
    document.getElementById('chat-error').style.display = 'none';
    
    // Show loading
    document.getElementById('chat-loading').style.display = 'flex';
    
    try {
        const response = await fetch(`${window.API_BASE}/chat-completion`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                prompt: prompt,
                max_tokens: 512,
                temperature: 0.7
            })
        });
        
        const data = await response.json();
        
        // Hide loading
        document.getElementById('chat-loading').style.display = 'none';
        
        if (data.success) {
            // Show response
            document.getElementById('chat-response-text').textContent = data.response;
            document.getElementById('chat-response').style.display = 'block';
            
            // Show metrics
            const metrics = data.metrics;
            document.getElementById('metric-latency').textContent = `${metrics.latency_ms} ms`;
            document.getElementById('metric-throughput').textContent = `${metrics.throughput_tps} tokens/sec`;
            document.getElementById('metric-prompt-tokens').textContent = metrics.prompt_tokens;
            document.getElementById('metric-completion-tokens').textContent = metrics.completion_tokens;
            document.getElementById('metric-total-tokens').textContent = metrics.total_tokens;
            document.getElementById('metric-time').textContent = `${metrics.time_seconds} seconds`;
            document.getElementById('chat-metrics').style.display = 'block';
        } else {
            // Show error
            const errorDiv = document.getElementById('chat-error');
            errorDiv.textContent = `Error: ${data.message}`;
            if (data.details) {
                errorDiv.textContent += ` - ${data.details}`;
            }
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        // Hide loading
        document.getElementById('chat-loading').style.display = 'none';
        
        // Show error
        const errorDiv = document.getElementById('chat-error');
        errorDiv.textContent = `Error: ${error.message}`;
        errorDiv.style.display = 'block';
    }
}

// Clear chat interface
function clearChat() {
    document.getElementById('chat-prompt').value = '';
    document.getElementById('chat-response').style.display = 'none';
    document.getElementById('chat-metrics').style.display = 'none';
    document.getElementById('chat-error').style.display = 'none';
    document.getElementById('chat-loading').style.display = 'none';
}

// Run benchmark tests
async function runBenchmark(testType) {
    // Hide previous results and errors
    document.getElementById('benchmark-results').style.display = 'none';
    document.getElementById('benchmark-error').style.display = 'none';
    
    // Show loading
    const loadingDiv = document.getElementById('benchmark-loading');
    const loadingText = document.getElementById('benchmark-loading-text');
    loadingDiv.style.display = 'flex';
    
    // Update loading text based on test type
    const testMessages = {
        'quick': 'Running quick latency test...',
        'standard': 'Running standard benchmark suite...',
        'full': 'Running comprehensive benchmark tests...',
        'stress': 'Running stress test to find limits...'
    };
    loadingText.textContent = testMessages[testType] || 'Running benchmark tests...';
    
    try {
        const response = await fetch(`${window.API_BASE}/run-benchmark`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ test_type: testType })
        });
        
        const data = await response.json();
        
        // Hide loading
        loadingDiv.style.display = 'none';
        
        if (data.success) {
            // Format and display results
            const results = data.results;
            const resultsContent = document.getElementById('benchmark-results-content');
            resultsContent.textContent = formatBenchmarkResults(results);
            document.getElementById('benchmark-results').style.display = 'block';
        } else {
            // Show error
            const errorDiv = document.getElementById('benchmark-error');
            errorDiv.textContent = `Error: ${data.message}`;
            errorDiv.style.display = 'block';
        }
    } catch (error) {
        // Hide loading
        loadingDiv.style.display = 'none';
        
        // Show error
        const errorDiv = document.getElementById('benchmark-error');
        errorDiv.textContent = `Error: ${error.message}`;
        errorDiv.style.display = 'block';
    }
}

// Format benchmark results for display
function formatBenchmarkResults(results) {
    let output = [];
    output.push(`Benchmark Results - ${new Date(results.timestamp).toLocaleString()}`);
    output.push(`Model: ${results.model}`);
    output.push('=' + '='.repeat(60));
    
    for (const [testName, testResult] of Object.entries(results.tests)) {
        if (testResult.error) {
            output.push(`\n${testName.toUpperCase()} TEST: ERROR - ${testResult.error}`);
            continue;
        }
        
        output.push(`\n${testName.toUpperCase()} TEST:`);
        output.push('-'.repeat(40));
        
        if (testName === 'latency') {
            output.push(`Requests: ${testResult.num_requests} | Success Rate: ${testResult.success_rate.toFixed(1)}%`);
            output.push(`\nLatency (ms):`);
            output.push(`  Mean:   ${testResult.latency.mean.toFixed(2)}`);
            output.push(`  Median: ${testResult.latency.median.toFixed(2)}`);
            output.push(`  P95:    ${testResult.latency.p95.toFixed(2)}`);
            output.push(`  P99:    ${testResult.latency.p99.toFixed(2)}`);
            output.push(`  Min:    ${testResult.latency.min.toFixed(2)}`);
            output.push(`  Max:    ${testResult.latency.max.toFixed(2)}`);
            output.push(`\nThroughput:`);
            output.push(`  Mean: ${testResult.throughput.mean_tokens_per_second.toFixed(1)} tokens/sec`);
            output.push(`  Max:  ${testResult.throughput.max_tokens_per_second.toFixed(1)} tokens/sec`);
            output.push(`  Total Tokens: ${testResult.throughput.total_tokens}`);
        }
        
        if (testName === 'concurrent') {
            output.push(`Concurrent Clients: ${testResult.num_concurrent_clients}`);
            output.push(`Requests per Client: ${testResult.requests_per_client}`);
            output.push(`Total Requests: ${testResult.total_requests} | Success: ${testResult.successful_requests}`);
            output.push(`Success Rate: ${testResult.success_rate.toFixed(1)}%`);
            output.push(`\nLatency Under Load (ms):`);
            output.push(`  Mean:   ${testResult.latency_under_load.mean.toFixed(2)}`);
            output.push(`  Median: ${testResult.latency_under_load.median.toFixed(2)}`);
            output.push(`  P95:    ${testResult.latency_under_load.p95.toFixed(2)}`);
            output.push(`  P99:    ${testResult.latency_under_load.p99.toFixed(2)}`);
            output.push(`\nThroughput Under Load:`);
            output.push(`  Mean: ${testResult.throughput_under_load.mean_tokens_per_second.toFixed(1)} tokens/sec`);
            output.push(`  Aggregate: ${testResult.throughput_under_load.aggregate_tokens_per_second.toFixed(1)} tokens/sec`);
            output.push(`  Requests/sec: ${testResult.requests_per_second.toFixed(2)}`);
        }
        
        if (testName === 'throughput') {
            output.push(`Test Duration: ${testResult.test_duration.toFixed(1)} seconds`);
            output.push(`Total Requests: ${testResult.total_requests} | Success: ${testResult.successful_requests}`);
            output.push(`Success Rate: ${testResult.success_rate.toFixed(1)}%`);
            output.push(`\nPerformance:`);
            output.push(`  Requests/sec: ${testResult.requests_per_second.toFixed(2)}`);
            output.push(`  Tokens/sec: ${testResult.tokens_per_second.toFixed(1)}`);
            output.push(`  Total Tokens: ${testResult.total_tokens_processed}`);
            output.push(`  Avg Tokens/Request: ${testResult.average_tokens_per_request.toFixed(1)}`);
        }
        
        if (testName === 'stress') {
            output.push(`Maximum Concurrent Tested: ${testResult.max_concurrent_tested}`);
            output.push(`Optimal Concurrent Clients: ${testResult.optimal_concurrent} (${testResult.peak_throughput.toFixed(2)} req/s peak)`);
            output.push(`Max Sustainable Load: ${testResult.max_sustainable_load} concurrent clients`);
            if (testResult.degradation_point) {
                output.push(`Performance Degradation Point: ${testResult.degradation_point} concurrent clients`);
            }
            output.push(`Breaking Point: ${testResult.breaking_point_found ? 'Found' : 'Not reached'}`);
            
            output.push(`\nLoad Test Results:`);
            for (const load of testResult.results_by_load) {
                let marker = '';
                if (load.success_rate < 50) marker = ' ❌';
                else if (load.success_rate < 95) marker = ' ⚠️';
                else if (load.success_rate === 100) marker = ' ✅';
                
                output.push(`  ${load.concurrent_clients} clients: ${load.success_rate.toFixed(1)}% success, ${load.mean_latency.toFixed(2)}ms mean, ${load.requests_per_second.toFixed(2)} req/s${marker}`);
                
                if (load.failed_requests > 0) {
                    output.push(`    └─ Failed requests: ${load.failed_requests}`);
                }
            }
            
            if (testResult.recommendations) {
                output.push(`\n📊 Recommendations:`);
                output.push(`  Optimal Concurrency: ${testResult.recommendations.optimal_concurrency}`);
                output.push(`  Suggested Max Workers: ${testResult.recommendations.suggested_max_workers}`);
                output.push(`  Note: ${testResult.recommendations.note}`);
            }
        }
    }
    
    return output.join('\n');
}

// Check service status on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check service status automatically on load
    checkServiceStatus();
});