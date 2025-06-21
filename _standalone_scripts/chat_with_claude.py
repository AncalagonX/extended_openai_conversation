#!/usr/bin/env python3
"""
Script to have a console-based conversation with Claude 3.7 Sonnet with tool use support.

Tool Error Handling:
- When a tool execution fails, the error is returned to Claude with is_error: true
- Claude will incorporate the error into its response or may retry with better inputs
- This follows Anthropic's recommended approach for tool error handling:
  https://docs.anthropic.com/en/docs/build-with-claude/tool-use (see "Troubleshooting errors" section)
"""

import sys
import os
import yaml
import json
import requests
import datetime
import time
from colorama import init, Fore, Style

# Initialize colorama for colored output
init()

# Path to the secrets file
SECRETS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "secrets.yaml")
MODEL_ID = "claude-3-7-sonnet-20250219"  # The specific model ID to use

# Define available tools
TOOLS = [
    {
        "name": "search_web",
        "description": "Search the web for information (simulated)",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    }
]

def load_api_key():
    """Load the Anthropic API key from secrets.yaml"""
    try:
        with open(SECRETS_FILE, 'r') as file:
            secrets = yaml.safe_load(file)
            return secrets.get('anthropic_api_key')
    except Exception as e:
        print(f"{Fore.RED}Error loading API key: {e}{Style.RESET_ALL}")
        sys.exit(1)

def send_message(api_key, messages, include_tools=True):
    """Send a message to Claude and get a response"""
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    # For debugging
    # print(f"{Fore.YELLOW}Sending messages:{Style.RESET_ALL}")
    # print(json.dumps(messages, indent=2))

    payload = {
        "model": MODEL_ID,
        "max_tokens": 1024,
        "messages": messages
    }

    # Include tools if specified
    if include_tools:
        payload["tools"] = TOOLS

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}API request failed: {e}{Style.RESET_ALL}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"{Fore.YELLOW}Response: {e.response.text}{Style.RESET_ALL}")
        return None

def format_response(content):
    """Format the response for display"""
    if isinstance(content, str):
        return content.replace('\\n', '\n')
    return content

def search_web(params):
    """Simulate a web search"""
    query = params.get("query", "")

    # Simulate search results
    results = [
        {
            "title": f"Result 1 for {query}",
            "snippet": f"This is a simulated search result for '{query}'. It contains some relevant information about the topic."
        },
        {
            "title": f"Result 2 for {query}",
            "snippet": f"Another simulated result related to '{query}'. This would typically come from a search engine."
        },
        {
            "title": f"Result 3 for {query}",
            "snippet": f"A third simulated search result for '{query}'. In a real implementation, this would contain actual web search results."
        }
    ]

    return {
        "query": query,
        "results": results,
        "search_time": time.time(),
        "result_count": len(results)
    }

def execute_tool(tool_name, tool_input):
    """Execute the specified tool with the given input"""
    print(f"{Fore.YELLOW}Executing tool: {tool_name}{Style.RESET_ALL}")

    try:
        if tool_name == "search_web":
            return search_web(tool_input)
        else:
            print(f"{Fore.RED}Unknown tool: {tool_name}{Style.RESET_ALL}")
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        error_message = f"Error executing tool {tool_name}: {str(e)}"
        print(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
        return {"error": error_message}

def process_tool_use_response(api_key, conversation, response_data):
    """Process a response where Claude wants to use a tool"""
    # Extract the tool use details before we add Claude's response to the conversation
    tool_use = None
    for content in response_data.get('content', []):
        if content.get('type') == 'tool_use':
            tool_use = content
            break

    if not tool_use:
        print(f"{Fore.RED}Tool use indicated but no tool_use content found{Style.RESET_ALL}")
        # Still add Claude's response to the conversation
        conversation.append({
            "role": "assistant",
            "content": response_data.get('content', [])
        })
        return None

    # Save the conversation state before adding anything
    conversation_copy = conversation.copy()

    # Display the tool use request
    tool_name = tool_use.get('name')
    tool_input = tool_use.get('input', {})
    tool_id = tool_use.get('id')

    print(f"{Fore.BLUE}Claude wants to use tool: {tool_name}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}Tool input: {json.dumps(tool_input, indent=2)}{Style.RESET_ALL}")

    # Execute the tool
    tool_result = execute_tool(tool_name, tool_input)

    # Check if there was an error
    is_error = 'error' in tool_result
    if is_error:
        print(f"{Fore.RED}Tool execution error: {tool_result['error']}{Style.RESET_ALL}")

    # Store the original response that contains the tool_use request
    assistant_message = {
        "role": "assistant",
        "content": response_data.get('content', [])
    }

    # Add Claude's response with the tool_use request to the conversation
    conversation.append(assistant_message)

    # Create a tool_result message - include is_error if tool execution failed
    tool_result_message = {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_id,
                "content": json.dumps(tool_result),
                "is_error": is_error
            }
        ]
    }

    # Add the tool result to the conversation
    conversation.append(tool_result_message)

    # Get Claude's final response with the tool result
    print(f"{Fore.YELLOW}Sending tool result to Claude...{Style.RESET_ALL}")
    try:
        final_response = send_message(api_key, conversation, include_tools=True)

        if final_response:
            # Add Claude's final response to the conversation
            final_message = {
                "role": "assistant",
                "content": final_response.get('content', [])
            }
            conversation.append(final_message)

            # Display the final response
            display_response(final_response)
        else:
            print(f"{Fore.RED}Failed to get final response after tool use{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Attempting conversation recovery...{Style.RESET_ALL}")

            # Restore original conversation state
            while len(conversation) > len(conversation_copy):
                conversation.pop()

            print(f"{Fore.GREEN}Conversation state recovered. Please try again.{Style.RESET_ALL}")

        return final_response
    except Exception as e:
        print(f"{Fore.RED}Error during tool result handling: {str(e)}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Restoring conversation state...{Style.RESET_ALL}")

        # Restore original conversation state
        while len(conversation) > len(conversation_copy):
            conversation.pop()

        print(f"{Fore.GREEN}Conversation state recovered. Please try again.{Style.RESET_ALL}")
        return None

def display_response(response_data):
    """Display Claude's response"""
    # Process each content block
    for content in response_data.get('content', []):
        if content.get('type') == 'text':
            text = content.get('text', '')
            # Skip displaying thinking blocks
            if "<thinking>" in text and "</thinking>" in text:
                thinking = text.split("<thinking>")[1].split("</thinking>")[0].strip()
                print(f"{Fore.YELLOW}Claude's thinking: {thinking}{Style.RESET_ALL}")
                # Remove the thinking section from the text
                text = text.replace(f"<thinking>{thinking}</thinking>", "").strip()

            if text:  # Only print if there's text after removing thinking blocks
                print(f"{Fore.BLUE}Claude: {Style.RESET_ALL}{format_response(text)}")

def main():
    """Main function to run the chat interface"""
    print(f"\n{Fore.GREEN}=== Chat with Claude 3.7 Sonnet with Tools ==={Style.RESET_ALL}")
    print(f"{Fore.CYAN}Type your messages and press Enter to send.{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Type 'exit', 'quit', or 'q' to end the conversation.{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Type 'reset' to reset the conversation history.{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Available tools: search_web{Style.RESET_ALL}\n")

    # Load API key
    api_key = load_api_key()
    if not api_key:
        print(f"{Fore.RED}No API key found in secrets.yaml{Style.RESET_ALL}")
        sys.exit(1)

    # Initialize conversation history
    conversation = []

    # Main chat loop
    while True:
        # Get user input
        user_input = input(f"{Fore.GREEN}You: {Style.RESET_ALL}")

        # Check for exit commands
        if user_input.lower() in ['exit', 'quit', 'q']:
            print(f"{Fore.YELLOW}Ending conversation. Goodbye!{Style.RESET_ALL}")
            break

        # Check for reset command
        if user_input.lower() == 'reset':
            conversation = []
            print(f"{Fore.YELLOW}Conversation history has been reset.{Style.RESET_ALL}")
            continue

        try:
            # Add user message to conversation
            conversation.append({"role": "user", "content": user_input})

            # Send to Claude and get response
            print(f"{Fore.YELLOW}Claude is thinking...{Style.RESET_ALL}")
            response_data = send_message(api_key, conversation)

            if not response_data:
                print(f"{Fore.RED}Failed to get a response from Claude.{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Try typing 'reset' to clear the conversation history.{Style.RESET_ALL}\n")
                continue

            # Check if Claude wants to use a tool
            stop_reason = response_data.get('stop_reason')
            if stop_reason == 'tool_use':
                # First display the response
                display_response(response_data)

                # Then process the tool use (this handles updating the conversation history)
                process_tool_use_response(api_key, conversation, response_data)
            else:
                # Regular text response
                display_response(response_data)

                # Add Claude's response to conversation history
                conversation.append({
                    "role": "assistant",
                    "content": response_data.get('content', [])
                })

            print()  # Add a newline for better readability
        except Exception as e:
            print(f"{Fore.RED}An error occurred: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Try typing 'reset' to clear the conversation history.{Style.RESET_ALL}\n")

if __name__ == "__main__":
    main()