#!/usr/bin/env python3
"""
Script to list all Anthropic models available with the provided API key.
"""

import sys
import os
import yaml
import requests
import json
from colorama import init, Fore, Style

# Initialize colorama for colored output
init()

# Path to the secrets file
SECRETS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "secrets.yaml")

def load_api_key():
    """Load the Anthropic API key from secrets.yaml"""
    try:
        with open(SECRETS_FILE, 'r') as file:
            secrets = yaml.safe_load(file)
            return secrets.get('anthropic_api_key')
    except Exception as e:
        print(f"{Fore.RED}Error loading API key: {e}{Style.RESET_ALL}")
        sys.exit(1)

def get_anthropic_models(api_key):
    """Fetch all available models from Anthropic API"""
    url = "https://api.anthropic.com/v1/models"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"  # You may need to update this version
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}API request failed: {e}{Style.RESET_ALL}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"{Fore.YELLOW}Response: {e.response.text}{Style.RESET_ALL}")
        sys.exit(1)

def display_models(models_data):
    """Display the models in a formatted way"""
    # Check for 'data' key in the response (current API structure)
    if 'data' in models_data:
        models_list = models_data['data']
    # Fallback to old 'models' key for backward compatibility
    elif 'models' in models_data:
        models_list = models_data['models']
    else:
        print(f"{Fore.RED}No models found in the API response.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Response structure: {json.dumps(models_data, indent=2)}{Style.RESET_ALL}")
        return

    print(f"\n{Fore.GREEN}=== Available Anthropic Models ==={Style.RESET_ALL}\n")

    for model in models_list:
        print(f"{Fore.CYAN}Model ID:{Style.RESET_ALL} {model.get('id', 'N/A')}")

        # Display model name if available (may be 'display_name' in newer API)
        display_name = model.get('display_name', model.get('name', 'N/A'))
        print(f"{Fore.CYAN}Name:{Style.RESET_ALL} {display_name}")

        # Display description if available
        if 'description' in model:
            print(f"{Fore.CYAN}Description:{Style.RESET_ALL} {model['description']}")

        # Display context window if available
        context_window = model.get('context_window', model.get('context_length', 'N/A'))
        print(f"{Fore.CYAN}Context Window:{Style.RESET_ALL} {context_window}")

        # Display max tokens if available
        if 'max_tokens' in model:
            print(f"{Fore.CYAN}Max Tokens:{Style.RESET_ALL} {model['max_tokens']}")

        # Display created_at if available (newer API)
        if 'created_at' in model:
            print(f"{Fore.CYAN}Created At:{Style.RESET_ALL} {model['created_at']}")

        print("-" * 50)

def main():
    """Main function"""
    print(f"{Fore.BLUE}Fetching available Anthropic models...{Style.RESET_ALL}")

    # Load API key
    api_key = load_api_key()
    if not api_key:
        print(f"{Fore.RED}No API key found in secrets.yaml{Style.RESET_ALL}")
        sys.exit(1)

    # Get and display models
    models_data = get_anthropic_models(api_key)

    # Debug output of raw response if needed
    # print(f"{Fore.YELLOW}Raw API Response:{Style.RESET_ALL}")
    # print(json.dumps(models_data, indent=2))

    display_models(models_data)

if __name__ == "__main__":
    main()