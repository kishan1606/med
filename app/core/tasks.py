"""
Background task management for async PDF processing.

Handles job queue, status tracking, and progress updates.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional, List, Callable, Any
from pathlib import Path
import logging

from app.api.models import ProcessingStatus, ProcessingProgress, ProcessingResult, ReportInfo

logger = logging.getLogger(__name__)


class JobManager:
    """Manages processing jobs and their status"""

    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.progress_callbacks: Dict[str, List[Callable]] = {}
        self._lock = asyncio.Lock()

    def create_job(self, filename: str, config: Optional[Dict] = None) -> str:
        """
        Create a new processing job.

        Args:
            filename: Name of the PDF file to process
            config: Optional configuration dictionary

        Returns:
            Job ID (UUID)
        """
        job_id = str(uuid.uuid4())

        self.jobs[job_id] = {
            "job_id": job_id,
            "filename": filename,
            "status": ProcessingStatus.PENDING,
            "progress": 0,
            "current_step": "Queued for processing",
            "result": None,
            "error": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "config": config or {},
        }

        logger.info(f"Created job {job_id} for file: {filename}")
        return job_id

    async def update_progress(
        self,
        job_id: str,
        progress: int,
        current_step: str,
        status: Optional[ProcessingStatus] = None,
    ) -> None:
        """
        Update job progress.

        Args:
            job_id: Job identifier
            progress: Progress percentage (0-100)
            current_step: Description of current step
            status: Optional status update
        """
        async with self._lock:
            if job_id not in self.jobs:
                logger.error(f"Job {job_id} not found for progress update")
                return

            self.jobs[job_id]["progress"] = progress
            self.jobs[job_id]["current_step"] = current_step
            self.jobs[job_id]["updated_at"] = datetime.now()

            if status:
                self.jobs[job_id]["status"] = status

            logger.debug(
                f"Job {job_id} progress: {progress}% - {current_step}"
            )

            # Trigger progress callbacks
            if job_id in self.progress_callbacks:
                progress_update = ProcessingProgress(
                    job_id=job_id,
                    status=self.jobs[job_id]["status"],
                    progress=progress,
                    current_step=current_step,
                )
                for callback in self.progress_callbacks[job_id]:
                    try:
                        await callback(progress_update)
                    except Exception as e:
                        logger.error(f"Error in progress callback: {e}")

    async def complete_job(
        self, job_id: str, result: ProcessingResult
    ) -> None:
        """
        Mark job as completed with results.

        Args:
            job_id: Job identifier
            result: Processing result
        """
        async with self._lock:
            if job_id not in self.jobs:
                logger.error(f"Job {job_id} not found for completion")
                return

            self.jobs[job_id]["status"] = ProcessingStatus.COMPLETED
            self.jobs[job_id]["progress"] = 100
            self.jobs[job_id]["current_step"] = "Processing completed"
            self.jobs[job_id]["result"] = result
            self.jobs[job_id]["updated_at"] = datetime.now()

            logger.info(f"Job {job_id} completed successfully")

    async def fail_job(self, job_id: str, error: str) -> None:
        """
        Mark job as failed with error message.

        Args:
            job_id: Job identifier
            error: Error message
        """
        async with self._lock:
            if job_id not in self.jobs:
                logger.error(f"Job {job_id} not found for failure update")
                return

            self.jobs[job_id]["status"] = ProcessingStatus.FAILED
            self.jobs[job_id]["error"] = error
            self.jobs[job_id]["current_step"] = "Processing failed"
            self.jobs[job_id]["updated_at"] = datetime.now()

            logger.error(f"Job {job_id} failed: {error}")

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job information.

        Args:
            job_id: Job identifier

        Returns:
            Job dictionary or None if not found
        """
        return self.jobs.get(job_id)

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """
        Get all jobs.

        Returns:
            List of job dictionaries
        """
        return list(self.jobs.values())

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job.

        Args:
            job_id: Job identifier

        Returns:
            True if deleted, False if not found
        """
        if job_id in self.jobs:
            del self.jobs[job_id]
            if job_id in self.progress_callbacks:
                del self.progress_callbacks[job_id]
            logger.info(f"Deleted job {job_id}")
            return True
        return False

    def register_progress_callback(
        self, job_id: str, callback: Callable
    ) -> None:
        """
        Register a callback for progress updates.

        Args:
            job_id: Job identifier
            callback: Async callback function
        """
        if job_id not in self.progress_callbacks:
            self.progress_callbacks[job_id] = []
        self.progress_callbacks[job_id].append(callback)

    def unregister_progress_callbacks(self, job_id: str) -> None:
        """
        Unregister all callbacks for a job.

        Args:
            job_id: Job identifier
        """
        if job_id in self.progress_callbacks:
            del self.progress_callbacks[job_id]

    async def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed/failed jobs.

        Args:
            max_age_hours: Maximum age of jobs to keep (hours)

        Returns:
            Number of jobs deleted
        """
        async with self._lock:
            now = datetime.now()
            to_delete = []

            for job_id, job in self.jobs.items():
                if job["status"] in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
                    age_hours = (now - job["updated_at"]).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        to_delete.append(job_id)

            for job_id in to_delete:
                del self.jobs[job_id]
                if job_id in self.progress_callbacks:
                    del self.progress_callbacks[job_id]

            if to_delete:
                logger.info(f"Cleaned up {len(to_delete)} old jobs")

            return len(to_delete)


# Global job manager instance
job_manager = JobManager()


async def cleanup_task():
    """Background task to periodically clean up old jobs"""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            deleted = await job_manager.cleanup_old_jobs(max_age_hours=24)
            if deleted > 0:
                logger.info(f"Auto-cleanup: removed {deleted} old jobs")
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
