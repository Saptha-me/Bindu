# Notifications Package

This package handles all notification-related functionality for the Bindu server.

## Structure

```
notifications/
├── __init__.py      # Package exports
└── push_manager.py  # Push notification management
```

## Components

### PushNotificationManager

Manages push notifications for task lifecycle events.

**Key Responsibilities:**
- Register and manage push notification configurations per task
- Build and send lifecycle event notifications
- Handle notification delivery errors gracefully
- Provide RPC handlers for push notification endpoints

**Usage:**

```python
from bindu.server.notifications import PushNotificationManager

# Initialize with manifest
push_manager = PushNotificationManager(manifest=agent_manifest)

# Check if push notifications are supported
if push_manager.is_push_supported():
    # Register a configuration
    push_manager.register_push_config(task_id, config)
    
    # Send lifecycle notification
    await push_manager.notify_lifecycle(task_id, context_id, "working", False)
```

## API Endpoints Handled

The PushNotificationManager provides handlers for these JSON-RPC methods:

- `tasks/pushNotification/set` - Set push notification configuration for a task
- `tasks/pushNotification/get` - Get push notification configuration
- `tasks/pushNotification/list` - List push notification configurations
- `tasks/pushNotification/delete` - Delete push notification configuration

## Event Format

Push notifications send lifecycle events in this format:

```json
{
  "event_id": "uuid",
  "sequence": 1,
  "timestamp": "2025-01-26T12:00:00Z",
  "kind": "status-update",
  "task_id": "task-uuid",
  "context_id": "context-uuid",
  "status": {
    "state": "working",
    "timestamp": "2025-01-26T12:00:00Z"
  },
  "final": false
}
```

## Error Handling

The manager handles errors gracefully:
- **NotificationDeliveryError**: Logs warning with status code
- **Validation errors**: Returns JSON-RPC error responses
- **Unexpected errors**: Logs error and continues

## Future Enhancements

This package can be extended with:
- Email notifications
- Webhook notifications
- SMS notifications
- In-app notifications
- Notification templates
- Notification preferences per user
