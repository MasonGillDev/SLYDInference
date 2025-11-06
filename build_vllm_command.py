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
            # vLLM uses --flag/--no-flag pattern for boolean arguments
            if key.startswith('enable_'):
                # For enable_* flags, vLLM uses --enable-foo/--no-enable-foo
                if value:
                    cmd_parts.append(cli_arg)
                else:
                    # Add --no-enable-* for false
                    no_flag = '--no-' + key.replace('_', '-')
                    cmd_parts.append(no_flag)
            elif value:
                # For other boolean flags, only add if true (they're store_true)
                cmd_parts.append(cli_arg)
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