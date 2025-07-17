#!/usr/bin/env python3
"""
Pebbling Protocol Schema Generator

This script generates OpenAPI schema JSON files from Pydantic models defined in types.py.
These schemas can be used with Swagger UI, ReDoc, or other OpenAPI tools.
"""

import os
import json
import inspect
import sys
from typing import Dict, List, Any, Type, Optional, Set, Tuple, Union, get_type_hints
from enum import Enum
from pydantic import BaseModel
from pydantic.fields import FieldInfo

# Import all models from types.py
from pebbling.protocol.types import (
    # Base models
    PebblingProtocolBaseModel, Role, RunMode,
    
    # Agent Models
    AgentManifest, AgentIdentity, AgentCapabilities, AgentMetrics, AgentTrust,
    MTLSConfiguration, IdentityProvider, KeycloakRole,
    
    # Trust Models
    TrustLevel, TrustCategory, TrustVerificationMethod,
    TrustVerificationRequest, TrustVerificationResponse, TrustVerificationResult,
    TrustVerificationParams,
    
    # Message & Content Models
    Message, MessageSendConfiguration, MessageSendParams,
    Part, TextPart, FilePart, DataPart, FileWithBytes, FileWithUri,
    
    # Task Models
    Task, TaskState, TaskStatus, Artifact, TaskIdParams,
    TaskStatusUpdateEvent, TaskArtifactUpdateEvent,
    
    # Negotiation Models
    NegotiationStatus, NegotiationSessionStatus,
    NegotiationProposal, NegotiationSession,
    
    # Payment Models
    PaymentActionType, PaymentStatus, PaymentMethod, BillingPeriod,
    PaymentAction,
    
    # JSON-RPC Models
    JSONRPCError, JSONRPCErrorResponse, JSONRPCResponse,
    
    # Request/Response Models
    SendMessageRequest, SendStreamingMessageRequest, 
    GetTaskRequest, CancelTaskRequest, TaskResubscriptionRequest,
    SendMessageSuccessResponse, SendStreamingMessageSuccessResponse,
    GetTaskSuccessResponse, CancelTaskSuccessResponse,
    
    # Error Models
    JSONParseError, InvalidRequestError, MethodNotFoundError, 
    InvalidParamsError, InternalError, TaskNotFoundError,
    TaskNotCancelableError, PushNotificationNotSupportedError,
    UnsupportedOperationError, ContentTypeNotSupportedError, 
    InvalidAgentResponseError,
)


def enhance_schema_with_examples_and_defaults(schema: Dict[str, Any], model: Type[PebblingProtocolBaseModel]) -> Dict[str, Any]:
    """Enhance schema with examples, descriptions, and proper default values from model fields"""
    if not hasattr(schema, 'get'):
        return schema
        
    # Handle properties
    if 'properties' in schema:
        for prop_name, prop_schema in schema['properties'].items():
            if hasattr(model, 'model_fields') and prop_name in model.model_fields:
                field = model.model_fields[prop_name]
                
                # Get examples from Field definition
                if (hasattr(field, 'json_schema_extra') and field.json_schema_extra and
                    'examples' in field.json_schema_extra):
                    prop_schema['example'] = field.json_schema_extra['examples'][0]
                
                # Add field description if available
                if hasattr(field, 'description') and field.description and 'description' not in prop_schema:
                    prop_schema['description'] = field.description
                    
                # Handle default values
                if hasattr(field, 'default') and field.default is not None and field.default is not ...:
                    # Don't add Ellipsis as default (means required field)
                    try:
                        # Check if it's serializable
                        json.dumps(field.default)
                        prop_schema['default'] = field.default
                    except (TypeError, OverflowError):
                        # Skip unserializable defaults
                        pass
                
                # Handle default_factory
                if hasattr(field, 'default_factory') and field.default_factory is not None:
                    try:
                        # Try to call the default_factory to get the default value
                        default_value = field.default_factory()
                        # Check if it's serializable
                        json.dumps(default_value)
                        prop_schema['default'] = default_value
                    except Exception:
                        # Skip if default_factory can't be called or result isn't serializable
                        pass
    
    # Add model description
    if hasattr(model, '__doc__') and model.__doc__ and 'description' not in schema:
        schema['description'] = model.__doc__.strip()
    
    return schema


def extract_enum_schema(enum_class: Type[Enum]) -> Dict[str, Any]:
    """Extract a detailed schema from an Enum class, including values and descriptions"""
    enum_values = [e.value for e in enum_class.__members__.values()]
    
    # Try to get descriptions for each enum value (if available in docstring)
    enum_descriptions = {}
    if enum_class.__doc__:
        for line in enum_class.__doc__.split('\n'):
            line = line.strip()
            # Look for patterns like "value = description" in docstring
            for member_name, member in enum_class.__members__.items():
                if line.startswith(f"{member_name} = ") or line.startswith(f"{member.value} = "):
                    parts = line.split(' = ', 1)
                    if len(parts) > 1:
                        enum_descriptions[member.value] = parts[1].strip()
    
    enum_schema = {
        "type": "string",
        "enum": enum_values
    }
    
    # Add descriptions
    if enum_class.__doc__:
        enum_schema["description"] = enum_class.__doc__.strip()
        
    if enum_descriptions:
        # If we have descriptions for individual values, add them as x-enum-descriptions
        enum_schema["x-enum-descriptions"] = enum_descriptions
    
    return enum_schema


def handle_root_model(model: Type, schema: Dict[str, Any]) -> Dict[str, Any]:
    """Handle RootModel types by extracting the inner type schema"""
    if not hasattr(model, '__annotations__'):
        return schema
        
    # Check if this is a RootModel by looking for root or __root__ attribute
    if hasattr(model, '__root__') or hasattr(model, 'root'):
        root_attr = '__root__' if hasattr(model, '__root__') else 'root'
        
        # Extract the actual schema from the root property
        if 'properties' in schema and root_attr in schema['properties']:
            root_schema = schema['properties'][root_attr]
            
            # Preserve model description and title if available
            if 'description' in schema:
                root_schema['description'] = schema['description']
            if 'title' in schema:
                root_schema['title'] = schema['title']
                
            # Preserve required info if relevant
            if 'required' in schema and root_attr in schema['required']:
                root_schema['required'] = True
                
            return root_schema
    
    return schema


def create_component_schemas() -> Dict[str, Any]:
    """Create component schemas for models"""
    components = {
        "$defs": {}
    }
    
    # List of models to include in the schema
    models = [
        # Base models
        Role, RunMode,
        
        # Agent Models
        AgentManifest, AgentIdentity, AgentCapabilities, AgentMetrics, AgentTrust,
        MTLSConfiguration, IdentityProvider, KeycloakRole,
        
        # Trust Models
        TrustLevel, TrustCategory, TrustVerificationMethod,
        TrustVerificationRequest, TrustVerificationResponse, TrustVerificationResult,
        TrustVerificationParams,
        
        # Message & Content Models
        Message, MessageSendConfiguration, MessageSendParams,
        Part, TextPart, FilePart, DataPart, FileWithBytes, FileWithUri,
        
        # Task Models
        Task, TaskState, TaskStatus, Artifact, TaskIdParams,
        TaskStatusUpdateEvent, TaskArtifactUpdateEvent,
        
        # Negotiation Models
        NegotiationStatus, NegotiationSessionStatus,
        NegotiationProposal, NegotiationSession,
        
        # Payment Models
        PaymentActionType, PaymentStatus, PaymentMethod, BillingPeriod,
        PaymentAction,
        
        # JSON-RPC Models
        JSONRPCError, JSONRPCErrorResponse, JSONRPCResponse,
        
        # Request/Response Models
        SendMessageRequest, SendStreamingMessageRequest, 
        GetTaskRequest, CancelTaskRequest, TaskResubscriptionRequest,
        SendMessageSuccessResponse, SendStreamingMessageSuccessResponse,
        GetTaskSuccessResponse, CancelTaskSuccessResponse,
        
        # Error Models
        JSONParseError, InvalidRequestError, MethodNotFoundError, 
        InvalidParamsError, InternalError, TaskNotFoundError,
        TaskNotCancelableError, PushNotificationNotSupportedError,
        UnsupportedOperationError, ContentTypeNotSupportedError, 
        InvalidAgentResponseError,
    ]
    
    # Track processed models for validation
    processed_models = set()
    
    # Process each model
    for model in models:
        model_name = model.__name__
        processed_models.add(model_name)
        
        # Handle different types of models
        if issubclass(model, Enum):
            # For Enum types
            try:
                # Create detailed enum schema with all values and descriptions
                enum_schema = extract_enum_schema(model)
                components["$defs"][model_name] = enum_schema
            except Exception as e:
                print(f"Warning: Could not process enum {model_name}: {str(e)}")
                continue
        else:
            # For Pydantic models and RootModels
            try:
                # Use Pydantic's schema generation - support both v1 and v2
                if hasattr(model, 'model_json_schema'):
                    schema = model.model_json_schema()
                elif hasattr(model, 'schema'):
                    schema = model.schema()
                else:
                    print(f"Warning: {model_name} has no schema generation method")
                    continue
                
                # Handle RootModel types (like Part)
                schema = handle_root_model(model, schema)
                
                # Enhance schema with examples, descriptions and defaults
                schema = enhance_schema_with_examples_and_defaults(schema, model)
                
                components["$defs"][model_name] = schema
            except Exception as e:
                print(f"Warning: Could not process model {model_name}: {str(e)}")
                continue
    
    return components


def create_openapi_spec() -> Dict[str, Any]:
    """Create JSON Schema spec compatible with datamodel-codegen"""
    # Get component schemas first
    components = create_component_schemas()
    
    # Create a JSON Schema format that datamodel-codegen can understand
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Pebbling Protocol",
        "description": "Pebbling Agent Communication Protocol",
        "type": "object",
        "properties": {}
    }
    
    # Add component schemas to the main schema
    schema.update(components)
    
    # Reference all definitions as top-level properties
    for model_name in schema["$defs"].keys():
        schema["properties"][model_name] = {"$ref": f"#/$defs/{model_name}"}
    
    return schema


def write_json_file(data: Dict[str, Any], filename: str) -> None:
    """Write data to JSON file"""
    with open(filename, 'w') as file:
        json.dump(data, file, indent=2)
    print(f"Generated {filename}")


def collect_all_model_classes(module_name: str) -> Set[str]:
    """Collect names of all model classes from the module"""
    import importlib
    import inspect
    
    module = importlib.import_module(module_name)
    model_names = set()
    
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and obj.__module__ == module.__name__:
            # Collect only classes defined in the target module
            if issubclass(obj, BaseModel) or issubclass(obj, Enum):
                model_names.add(name)
    
    return model_names


def validate_schema_completeness(schema: Dict[str, Any], module_name: str = "pebbling.protocol.types") -> Tuple[List[str], Dict[str, List[str]]]:
    """
    Validate that all models from the source module are included in the schema.
    
    Returns:
        Tuple containing:
        - List of missing model names
        - Dict of models with missing fields {model_name: [field_names]}
    """
    # Get all model classes defined in the module
    all_model_names = collect_all_model_classes(module_name)
    
    # Check which models are missing from the schema
    schema_model_names = set(schema["$defs"].keys())
    missing_models = sorted(list(all_model_names - schema_model_names))
    
    # For models that are included, check for missing fields
    models_with_missing_fields = {}
    import importlib
    module = importlib.import_module(module_name)
    
    for model_name in schema_model_names:
        if not hasattr(module, model_name):
            continue
            
        model = getattr(module, model_name)
        
        # Skip non-Pydantic models (like Enums)
        if not hasattr(model, 'model_fields'):
            continue
            
        model_schema = schema["$defs"][model_name]
        schema_props = model_schema.get('properties', {})
        
        # Get field names from the original model
        model_field_names = set(model.model_fields.keys())
        schema_field_names = set(schema_props.keys())
        
        missing_fields = sorted(list(model_field_names - schema_field_names))
        if missing_fields:
            models_with_missing_fields[model_name] = missing_fields
    
    return missing_models, models_with_missing_fields


def main() -> None:
    """Generate schema files"""
    # Output directory - same as the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Generate JSON Schema spec
    json_schema = create_openapi_spec()
    
    # Validate schema completeness
    missing_models, models_with_missing_fields = validate_schema_completeness(json_schema)
    
    # Report any missing models or fields
    if missing_models:
        print("WARNING: The following models are missing from the schema:")
        for model in missing_models:
            print(f"  - {model}")
        print("\nYou should add these models to the 'models' list in create_component_schemas()")
    
    if models_with_missing_fields:
        print("\nWARNING: The following models have missing fields:")
        for model, fields in models_with_missing_fields.items():
            print(f"  - {model}: Missing fields: {', '.join(fields)}")
    
    # Main output file
    output_file = os.path.join(script_dir, "pebbling_protocol.json")
    
    # Write main spec file
    write_json_file(json_schema, output_file)
    
    # Also generate individual component files for easier consumption
    components_dir = os.path.join(script_dir, "components")
    os.makedirs(components_dir, exist_ok=True)
    
    # Write individual schema files
    if "$defs" in json_schema:
        for schema_name, schema in json_schema["$defs"].items():
            schema_file = os.path.join(components_dir, f"{schema_name}.json")
            write_json_file(schema, schema_file)
    
    # Success message
    print(f"\nSchema generation complete. Generated {len(json_schema['$defs'])} component schemas.")
    print(f"Main schema file: {output_file}")
    print(f"Component schemas: {components_dir}/")


if __name__ == "__main__":
    main()
