"""
Test client for the gRPC and JSON-RPC agent protocols.

This script:
1. Implements both gRPC and JSON-RPC clients
2. Tests all the agent protocol methods (status, text, image, audio, video)
3. Provides a simple CLI to choose which protocol to test
"""

import argparse
import base64
import json
import os
import sys
import time
from typing import Dict, Any, Optional, List, Union
import uuid

# For gRPC client
import grpc
from pebble.protos import agent_pb2
from pebble.protos import agent_pb2_grpc

# For JSON-RPC client
import httpx

# Image handling
from PIL import Image
import io


def test_grpc_client(host: str, port: int):
    """Test the gRPC client against a running gRPC server."""
    print(f"\n=== Testing gRPC client on {host}:{port} ===")
    
    # Create a channel and stub
    channel = grpc.insecure_channel(f"{host}:{port}")
    stub = agent_pb2_grpc.AgentServiceStub(channel)
    
    try:
        # Test GetStatus
        print("\nTesting GetStatus...")
        status_response = stub.GetStatus(agent_pb2.Empty())
        print(f"Status: {status_response.status}")
        print(f"Agent: {status_response.name} ({status_response.agent_id})")
        print(f"Framework: {status_response.framework}")
        print(f"Capabilities: {', '.join(status_response.capabilities)}")
        print(f"Metadata: {status_response.metadata}")
        
        # Test ProcessAction (text)
        print("\nTesting ProcessAction (text)...")
        action_request = agent_pb2.ActionRequest(
            message="Hello, agent! How are you?",
            role="user"
        )
        action_response = stub.ProcessAction(action_request)
        print(f"Response: {action_response.message}")
        
        # Test ViewImage with image
        print("\nTesting ViewImage with test image...")
        # Create a simple test image
        test_image = create_test_image()
        image_bytes = io.BytesIO()
        test_image.save(image_bytes, format='PNG')
        image_bytes = image_bytes.getvalue()
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Create image request
        image_request = agent_pb2.ImageRequest(
            base64_image=image_b64,
            mime_type="image/png",
            width=test_image.width,
            height=test_image.height
        )
        image_response = stub.ViewImage(image_request)
        print(f"Image Response: {image_response.message}")
        
        # Test ViewVideo with video URL
        print("\nTesting ViewVideo with video URL...")
        # Use a video URL instead of actual video data for simplicity
        video_url = "https://example.com/test_video.mp4"
        video_request = agent_pb2.VideoRequest(
            url=video_url,
            mime_type="video/mp4",
            width=1280,
            height=720,
            duration=10.5  # 10.5 seconds
        )
        video_response = stub.ViewVideo(video_request)
        print(f"Video Response: {video_response.message}")
        
        # Test Listen with audio URL
        print("\nTesting Listen with audio URL...")
        # Use an audio URL instead of actual audio data for simplicity
        audio_url = "https://example.com/test_audio.mp3"
        audio_request = agent_pb2.AudioRequest(
            url=audio_url
        )
        audio_response = stub.Listen(audio_request)
        print(f"Audio Response: {audio_response.message}")
        
        print("\ngRPC tests completed successfully!")
        
    except grpc.RpcError as e:
        print(f"gRPC error: {e.code()}: {e.details()}")
    finally:
        channel.close()


def debug_jsonrpc_server(host: str, port: int):
    """Debug the JSON-RPC server to check available endpoints."""
    try:
        # Try to get the OpenAPI documentation
        response = httpx.get(f"http://{host}:{port}/openapi.json")
        if response.status_code == 200:
            print(f"\nOpenAPI definition found at {host}:{port}/openapi.json")
            api_def = response.json()
            if "paths" in api_def:
                print("Available endpoints:")
                for path in api_def["paths"]:
                    print(f"  {path}")
            return
    except httpx.RequestError:
        pass
    
    # If we can't get OpenAPI, try a basic GET request to the root
    try:
        response = httpx.get(f"http://{host}:{port}/")
        print(f"\nGET / response: {response.status_code}")
        if response.status_code == 200:
            print("Server responded with 200 OK. This is a good sign.")
        else:
            print(f"Server responded with {response.status_code}: {response.text}")
    except httpx.RequestError as e:
        print(f"\nError connecting to server: {e}")


def test_jsonrpc_client(host: str, port: int):
    """Test the JSON-RPC client against a running JSON-RPC server."""
    print(f"\n=== Testing JSON-RPC client on {host}:{port} ===")
    
    # Debug the server first
    debug_jsonrpc_server(host, port)
    
    # Base URL for JSON-RPC - try both with and without /jsonrpc
    base_url = f"http://{host}:{port}/jsonrpc"
    headers = {"Content-Type": "application/json"}
    
    try:
        # Test get_status
        print("\nTesting get_status...")
        status_request = {
            "jsonrpc": "2.0",
            "method": "get_status",
            "params": {},
            "id": 1
        }
        
        status_response = httpx.post(base_url, headers=headers, json=status_request)
        if status_response.status_code == 200:
            status_data = status_response.json()
            if "result" in status_data:
                result = status_data["result"]
                print(f"Status: {result.get('status')}")
                print(f"Agent: {result.get('name')} ({result.get('agent_id')})")
                print(f"Framework: {result.get('framework')}")
                print(f"Capabilities: {', '.join(result.get('capabilities', []))}")
                print(f"Metadata: {result.get('metadata')}")
            else:
                print(f"Error: {status_data.get('error')}")
        else:
            print(f"Error: {status_response.status_code} - {status_response.text}")
            
            # If we got a 404, try without the /jsonrpc path
            if status_response.status_code == 404:
                print("\nTrying root endpoint instead...")
                alt_url = f"http://{host}:{port}/"
                status_response = httpx.post(alt_url, headers=headers, json=status_request)
                if status_response.status_code == 200:
                    print(f"Success with root endpoint! Use {alt_url} for future requests.")
                    # Update base_url for future requests
                    base_url = alt_url
                else:
                    print(f"Also failed with root endpoint: {status_response.status_code}")
        
        # Test process_action (text)
        print("\nTesting process_action (text)...")
        action_request = {
            "jsonrpc": "2.0",
            "method": "process_action",
            "params": {
                "message": "Hello, agent! How are you?",
                "role": "user"
            },
            "id": 2
        }
        
        action_response = httpx.post(base_url, headers=headers, json=action_request)
        if action_response.status_code == 200:
            action_data = action_response.json()
            if "result" in action_data:
                result = action_data["result"]
                print(f"Response: {result.get('message')}")
            else:
                print(f"Error: {action_data.get('error')}")
        else:
            print(f"Error: {action_response.status_code} - {action_response.text}")
        
        # Test process_request with image
        print("\nTesting process_request with image...")
        # Create a simple test image
        test_image = create_test_image()
        image_bytes = io.BytesIO()
        test_image.save(image_bytes, format='PNG')
        image_bytes = image_bytes.getvalue()
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Create image request
        image_request = {
            "jsonrpc": "2.0",
            "method": "process_request",
            "params": {
                "request_type": "image",
                "base64_image": image_b64,
                "mime_type": "image/png",
                "width": test_image.width,
                "height": test_image.height
            },
            "id": 3
        }
        
        image_response = httpx.post(base_url, headers=headers, json=image_request)
        if image_response.status_code == 200:
            image_data = image_response.json()
            if "result" in image_data:
                result = image_data["result"]
                print(f"Image Response: {result.get('message')}")
            else:
                print(f"Error: {image_data.get('error')}")
        else:
            print(f"Error: {image_response.status_code} - {image_response.text}")
        
        # Test process_request with video URL
        print("\nTesting process_request with video URL...")
        video_url = "https://example.com/test_video.mp4"
        video_request = {
            "jsonrpc": "2.0",
            "method": "process_request",
            "params": {
                "request_type": "video",
                "url": video_url,
                "mime_type": "video/mp4",
                "width": 1280,
                "height": 720,
                "duration": 10.5
            },
            "id": 4
        }
        
        video_response = httpx.post(base_url, headers=headers, json=video_request)
        if video_response.status_code == 200:
            video_data = video_response.json()
            if "result" in video_data:
                result = video_data["result"]
                print(f"Video Response: {result.get('message')}")
            else:
                print(f"Error: {video_data.get('error')}")
        else:
            print(f"Error: {video_response.status_code} - {video_response.text}")
        
        # Test process_request with audio URL
        print("\nTesting process_request with audio URL...")
        audio_url = "https://example.com/test_audio.mp3"
        audio_request = {
            "jsonrpc": "2.0",
            "method": "process_request",
            "params": {
                "request_type": "audio",
                "url": audio_url
            },
            "id": 5
        }
        
        audio_response = httpx.post(base_url, headers=headers, json=audio_request)
        if audio_response.status_code == 200:
            audio_data = audio_response.json()
            if "result" in audio_data:
                result = audio_data["result"]
                print(f"Audio Response: {result.get('message')}")
            else:
                print(f"Error: {audio_data.get('error')}")
        else:
            print(f"Error: {audio_response.status_code} - {audio_response.text}")
        
        print("\nJSON-RPC tests completed successfully!")
        
    except httpx.RequestError as e:
        print(f"JSON-RPC request error: {e}")


def create_test_image(width=100, height=100, color=(255, 0, 0)):
    """Create a simple test image with the given dimensions and color."""
    return Image.new('RGB', (width, height), color)


def main():
    """Main entry point for the client test script."""
    parser = argparse.ArgumentParser(description="Test agent protocol clients")
    parser.add_argument("--protocol", choices=["grpc", "jsonrpc", "both"], default="both",
                      help="Which protocol client to test")
    parser.add_argument("--host", default="localhost", help="Host where server is running")
    parser.add_argument("--grpc-port", type=int, default=50051, help="Port for gRPC server")
    parser.add_argument("--jsonrpc-port", type=int, default=8000, help="Port for JSON-RPC server")
    args = parser.parse_args()
    
    # Run tests based on the chosen protocol
    if args.protocol in ["grpc", "both"]:
        test_grpc_client(args.host, args.grpc_port)
    
    if args.protocol in ["jsonrpc", "both"]:
        test_jsonrpc_client(args.host, args.jsonrpc_port)


if __name__ == "__main__":
    main()