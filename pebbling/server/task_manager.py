"""
|---------------------------------------------------------|
|                                                         |
|                 Give Feedback / Get Help                |
| https://github.com/Pebbling-ai/pebble/issues/new/choose |
|                                                         |
|---------------------------------------------------------|

🍔 **The Pebbling Task Manager: A Burger Restaurant Architecture**

This module defines the TaskManager - the **Restaurant Manager** of our AI agent ecosystem.
Think of it like running a high-end burger restaurant where customers place orders,
and we coordinate the entire kitchen operation to deliver perfect results.

## 🏢 **Restaurant Components**

- **TaskManager** (Restaurant Manager): Coordinates the entire operation, handles customer requests
- **Scheduler** (Order Queue System): Manages the flow of orders to the kitchen  
- **Worker** (Chef): Actually cooks the burgers (executes AI agent tasks)
- **Runner** (Recipe Book): Defines how each dish is prepared and plated
- **Storage** (Restaurant Database): Keeps track of orders, ingredients, and completed dishes

## 🏗️ **Restaurant Architecture**

```
  +-----------------+
  |   Front Desk    |  🎯 Customer Interface
  |  (HTTP Server)  |     (Takes Orders)
  +-------+---------+
          |
          | 📝 Order Placed
          v
  +-------+---------+
  |                 |  👨‍💼 Restaurant Manager
  |   TaskManager   |     (Coordinates Everything)
  |   (Manager)     |<-----------------+
  +-------+---------+                  |
          |                            |
          | 📋 Send to Kitchen         | 💾 Track Everything
          v                            v
  +------------------+         +----------------+
  |                  |         |                |  📊 Restaurant Database
  |    Scheduler     |         |    Storage     |     (Orders & History)
  |  (Order Queue)   |         |  (Database)    |
  +------------------+         +----------------+
          |                            ^
          | 🍳 Kitchen Ready           |
          v                            | 📝 Update Status
  +------------------+                 |
  |                  |                 |  👨‍🍳 Head Chef
  |     Worker       |-----------------+     (Executes Tasks)
  |     (Chef)       |
  +------------------+
          |
          | 📖 Follow Recipe
          v
  +------------------+
  |     Runner       |  📚 Recipe Book
  |  (Recipe Book)   |     (Task Execution Logic)
  +------------------+
```

## 🔄 **Restaurant Workflow**

1. **📞 Order Received**: Customer places order at Front Desk (HTTP Server)
2. **👨‍💼 Manager Takes Control**: TaskManager receives the order and logs it
3. **💾 Order Logged**: Initial order details stored in Restaurant Database (Storage)
4. **📋 Kitchen Queue**: TaskManager sends order to Scheduler (Order Queue System)
5. **🍳 Chef Assignment**: Scheduler determines when Chef (Worker) is available
6. **📖 Recipe Lookup**: Worker consults Runner (Recipe Book) for execution steps
7. **👨‍🍳 Cooking Process**: Runner defines how the task is prepared and executed
8. **📝 Progress Updates**: Worker continuously updates order status in Database
9. **🍔 Order Complete**: Final result stored and marked as ready
10. **📞 Customer Notification**: Manager can provide status updates anytime
11. **✅ Order Delivered**: Customer receives their perfectly prepared result

## 🎯 **Key Benefits**

- **🔄 Scalable**: Multiple chefs can work simultaneously
- **📊 Trackable**: Every order is logged and monitored
- **🛡️ Reliable**: Failed orders can be retried or cancelled
- **⚡ Efficient**: Smart queue management prevents kitchen overload
- **📈 Observable**: Full visibility into restaurant operations

*"Just like a well-run restaurant, every task gets the attention it deserves!"* 🌟

Thank you users! We ❤️ you! - 🐧
"""

from __future__ import annotations as _annotations

import uuid
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any

from .scheduler import Scheduler
from .storage import Storage

from pebbling.common.protocol.types import (
    CancelTaskRequest,
    CancelTaskResponse,
    GetTaskPushNotificationRequest,
    GetTaskPushNotificationResponse,
    GetTaskRequest,
    GetTaskResponse,
    ResubscribeTaskRequest,
    SendMessageRequest,
    SendMessageResponse,
    SetTaskPushNotificationRequest,
    SetTaskPushNotificationResponse,
    StreamMessageRequest,
    StreamMessageResponse,
    TaskNotFoundError,
    TaskSendParams,
)


@dataclass
class TaskManager:
    """A task manager responsible for managing tasks."""

    scheduler: Scheduler
    storage: Storage[Any]

    _aexit_stack: AsyncExitStack | None = field(default=None, init=False)

    async def __aenter__(self):
        self._aexit_stack = AsyncExitStack()
        await self._aexit_stack.__aenter__()
        await self._aexit_stack.enter_async_context(self.scheduler)

        return self

    @property
    def is_running(self) -> bool:
        return self._aexit_stack is not None

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        if self._aexit_stack is None:
            raise RuntimeError('TaskManager was not properly initialized.')
        await self._aexit_stack.__aexit__(exc_type, exc_value, traceback)
        self._aexit_stack = None

    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        """Send a message using the Pebble protocol."""
        request_id = request['id']
        message = request['params']['message']
        context_id = message.get('context_id', str(uuid.uuid4()))

        task = await self.storage.submit_task(context_id, message)

        scheduler_params: TaskSendParams = {'id': task['id'], 'context_id': context_id, 'message': message}
        config = request['params'].get('configuration', {})
        history_length = config.get('history_length')
        if history_length is not None:
            scheduler_params['history_length'] = history_length

        await self.scheduler.run_task(scheduler_params)
        return SendMessageResponse(jsonrpc='2.0', id=request_id, result=task)

    async def get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        """Get a task, and return it to the client.

        No further actions are needed here.
        """
        task_id = request['params']['id']
        history_length = request['params'].get('history_length')
        task = await self.storage.load_task(task_id, history_length)
        if task is None:
            return GetTaskResponse(
                jsonrpc='2.0',
                id=request['id'],
                error=TaskNotFoundError(code=-32001, message='Task not found'),
            )
        return GetTaskResponse(jsonrpc='2.0', id=request['id'], result=task)

    async def cancel_task(self, request: CancelTaskRequest) -> CancelTaskResponse:
        await self.scheduler.cancel_task(request['params'])
        task = await self.storage.load_task(request['params']['id'])
        if task is None:
            return CancelTaskResponse(
                jsonrpc='2.0',
                id=request['id'],
                error=TaskNotFoundError(code=-32001, message='Task not found'),
            )
        return CancelTaskResponse(jsonrpc='2.0', id=request['id'], result=task)

    async def stream_message(self, request: StreamMessageRequest) -> StreamMessageResponse:
        """Stream messages using Server-Sent Events."""
        raise NotImplementedError('message/stream method is not implemented yet.')

    async def set_task_push_notification(
        self, request: SetTaskPushNotificationRequest
    ) -> SetTaskPushNotificationResponse:
        raise NotImplementedError('SetTaskPushNotification is not implemented yet.')

    async def get_task_push_notification(
        self, request: GetTaskPushNotificationRequest
    ) -> GetTaskPushNotificationResponse:
        raise NotImplementedError('GetTaskPushNotification is not implemented yet.')

    async def resubscribe_task(self, request: ResubscribeTaskRequest) -> None:
        raise NotImplementedError('Resubscribe is not implemented yet.')