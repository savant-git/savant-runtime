from __future__ import annotations

from dispatcher.DISPATCHER import dispatcher
from scheduler.SCHEDULER import scheduler
from bus.EVENT_BUS import bus


class ExecutionManager:

    def dispatch(self, capability, payload):
        return dispatcher.dispatch(capability, payload)

    def schedule(self, priority, fn, *args, **kwargs):
        scheduler.schedule(priority, fn, *args, **kwargs)

    def run(self):
        scheduler.run()

    def publish(self, event, payload):
        bus.publish(event, payload)

    def subscribe(self, event, handler):
        bus.subscribe(event, handler)


manager = ExecutionManager()
