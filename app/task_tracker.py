import asyncio
import logging

logger = logging.getLogger(__name__)

class BackgroundTaskTracker:
    def __init__(self):
        self.tasks: set[asyncio.Task] = set()

    def create_task(self, coro):
        """Create a task and add it to the tracker."""
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    async def wait_all(self, timeout: float = 5.0):
        """Wait for all running tasks to complete during shutdown."""
        if not self.tasks:
            return
            
        logger.info(f"Waiting for {len(self.tasks)} background tasks to complete...")
        try:
            # Shield prevents cancellation from propagating downwards during wait
            await asyncio.wait_for(asyncio.shield(asyncio.gather(*self.tasks, return_exceptions=True)), timeout=timeout)
            logger.info("All background tasks completed successfully.")
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for background tasks. {len(self.tasks)} tasks still pending.")

# Global singleton
background_tasks = BackgroundTaskTracker()
