#!/usr/bin/env python3
"""
Build vLLM command dynamically from config file
"""
import json
import argparse

def build_command(config_file):
    """Build vLLM command from config file"""
    # Load config file
    with open(config_file) as f:
        config = json.load(f)
    
    # Start building command
    cmd_parts = ['python -m vllm.entrypoints.openai.api_server']
    
    # Process each config parameter
    for key, value in config.items():
        # Convert underscore to hyphen for CLI arguments
        cli_arg = '--' + key.replace('_', '-')
        
        # Handle different value types
        if isinstance(value, bool):
            # Always pass boolean flags explicitly
            # vLLM uses store_true for most flags, but we'll be explicit
            if value:
                cmd_parts.append(cli_arg)
            else:
                # For false values, add --no-{flag} or skip based on vLLM's expectations
                # Most vLLM boolean flags are store_true, so false means don't add them
                # But for some like enable_prefix_caching, we need to explicitly disable
                if key.startswith('enable_'):
                    # Convert enable_* false to disable-*
                    disable_flag = '--disable-' + key.replace('enable_', '').replace('_', '-')
                    cmd_parts.append(disable_flag)
                elif key.startswith('disable_'):
                    # disable_* false means we want the feature enabled (don't add the flag)
                    pass
                # For other boolean flags, false means don't add them
        elif value is not None and value != '':
            # Add parameter with its value
            cmd_parts.append(f"{cli_arg} {value}")
    
    return ' '.join(cmd_parts)

def display_config(config_file):
    """Display configuration in a readable format"""
    with open(config_file) as f:
        config = json.load(f)
    
    for key, value in config.items():
        if isinstance(value, bool):
            value = 'enabled' if value else 'disabled'
        print(f"  {key.replace('_', ' ').title()}: {value}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build vLLM command from config')
    parser.add_argument('config_file', help='Path to config JSON file')
    parser.add_argument('--display', action='store_true', 
                        help='Display config instead of building command')
    
    args = parser.parse_args()
    
    if args.display:
        display_config(args.config_file)
    else:
        print(build_command(args.config_file))