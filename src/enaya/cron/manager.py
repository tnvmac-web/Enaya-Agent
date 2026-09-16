#!/usr/bin/env python3
"""
Enaya Agent - Cron System
Full cron job implementation with scheduling, skill attachment, and cross-platform delivery.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import croniter

from enaya.cli.config import load_config
from enaya.gateway.runner import GatewayRunner
from enaya.run_agent import create_agent

# =============================================================================
# Cron Data Classes
# =============================================================================

class CronScheduleType(Enum):
    CRON = "cron"
    INTERVAL = "interval"
    ONESHOT = "oneshot"


@dataclass
class CronJob:
    """Cron job definition."""
    id: str
    name: str
    schedule: str  # cron expression, interval in seconds, or ISO timestamp
    schedule_type: CronScheduleType = CronScheduleType.CRON
    prompt: str = ""
    model: str | None = None
    provider: str | None = None
    toolsets: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    max_turns: int = 500
    fallback_providers: list[tuple[str, str]] = field(default_factory=list)
    deliver: dict = field(default_factory=dict)  # platform, chat_type, chat_id
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_run: float | None = None
    next_run: float | None = None
    run_count: int = 0
    last_result: str | None = None
    last_error: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class CronJobResult:
    """Result of a cron job execution."""
    job_id: str
    success: bool
    result: str | None = None
    error: str | None = None
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    duration: float = 0.0


# =============================================================================
# Cron Manager
# =============================================================================

class CronManager:
    """Manages cron jobs with scheduling and execution."""

    def __init__(self, profile: str = "default", gateway: GatewayRunner = None):
        self.profile = profile
        self.gateway = gateway
        self.config = load_config(profile)
        self.jobs_file = Path.home() / ".enaya" / "cron" / "jobs.json"
        self.jobs_file.parent.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, CronJob] = {}
        self._running = False
        self._scheduler_task: asyncio.Task | None = None
        self._running_jobs: dict[str, asyncio.Task] = {}
        self._load_jobs()

    def _load_jobs(self) -> None:
        """Load jobs from JSON file."""
        if self.jobs_file.exists():
            try:
                with open(self.jobs_file) as f:
                    data = json.load(f)

                for job_data in data.get("jobs", []):
                    job = CronJob(**job_data)
                    # Convert fallback_providers from list of lists to tuples
                    if job.fallback_providers and isinstance(job.fallback_providers[0], list):
                        job.fallback_providers = [tuple(p) for p in job.fallback_providers]
                    self.jobs[job.id] = job

                    # Calculate next run
                    self._calculate_next_run(job)
            except Exception as e:
                print(f"Failed to load cron jobs: {e}")

    def _save_jobs(self) -> None:
        """Save jobs to JSON file."""
        try:
            data = {
                "jobs": [
                    {
                        **job.__dict__,
                        "fallback_providers": [list(p) for p in job.fallback_providers],
                        "schedule_type": job.schedule_type.value,
                    }
                    for job in self.jobs.values()
                ]
            }
            with open(self.jobs_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save cron jobs: {e}")

    def _calculate_next_run(self, job: CronJob) -> None:
        """Calculate next run time for a job."""
        if not job.enabled:
            job.next_run = None
            return

        if job.schedule_type == CronScheduleType.CRON:
            try:
                cron = croniter.croniter(job.schedule, time.time())
                job.next_run = cron.get_next(float)
            except Exception:
                job.next_run = None

        elif job.schedule_type == CronScheduleType.INTERVAL:
            try:
                interval = float(job.schedule)
                base = job.last_run or time.time()
                job.next_run = base + interval
            except Exception:
                job.next_run = None

        elif job.schedule_type == CronScheduleType.ONESHOT:
            try:
                job.next_run = float(job.schedule)
            except Exception:
                job.next_run = None

    def add_job(
        self,
        name: str,
        schedule: str,
        prompt: str,
        schedule_type: CronScheduleType = CronScheduleType.CRON,
        model: str = None,
        provider: str = None,
        toolsets: list[str] = None,
        skills: list[str] = None,
        max_turns: int = 500,
        fallback_providers: list[tuple[str, str]] = None,
        deliver: dict = None,
        metadata: dict = None,
    ) -> str:
        """Add a new cron job."""
        import uuid
        job_id = str(uuid.uuid4())[:12]

        job = CronJob(
            id=job_id,
            name=name,
            schedule=schedule,
            schedule_type=schedule_type,
            prompt=prompt,
            model=model,
            provider=provider,
            toolsets=toolsets or [],
            skills=skills or [],
            max_turns=max_turns,
            fallback_providers=fallback_providers or [],
            deliver=deliver or {},
            metadata=metadata or {},
        )

        self._calculate_next_run(job)
        self.jobs[job_id] = job
        self._save_jobs()
        return job_id

    def remove_job(self, job_id: str) -> bool:
        """Remove a cron job."""
        if job_id in self.jobs:
            # Cancel running job if any
            if job_id in self._running_jobs:
                self._running_jobs[job_id].cancel()
                del self._running_jobs[job_id]

            del self.jobs[job_id]
            self._save_jobs()
            return True
        return False

    def enable_job(self, job_id: str, enabled: bool = True) -> bool:
        """Enable or disable a cron job."""
        if job_id in self.jobs:
            self.jobs[job_id].enabled = enabled
            self._calculate_next_run(self.jobs[job_id])
            self._save_jobs()
            return True
        return False

    def get_job(self, job_id: str) -> CronJob | None:
        return self.jobs.get(job_id)

    def list_jobs(self) -> list[CronJob]:
        return list(self.jobs.values())

    async def start(self) -> None:
        """Start the cron scheduler."""
        if self._running:
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        print("Cron scheduler started")

    async def stop(self) -> None:
        """Stop the cron scheduler."""
        self._running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        # Cancel running jobs
        for task in self._running_jobs.values():
            task.cancel()
        self._running_jobs.clear()

        print("Cron scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                now = time.time()

                for job in list(self.jobs.values()):
                    if not job.enabled or job.next_run is None:
                        continue

                    if now >= job.next_run:
                        # Execute job
                        task = asyncio.create_task(self._execute_job(job))
                        self._running_jobs[job.id] = task

                # Clean up completed tasks
                completed = [
                    job_id for job_id, task in self._running_jobs.items()
                    if task.done()
                ]
                for job_id in completed:
                    del self._running_jobs[job_id]

            except Exception as e:
                print(f"Scheduler error: {e}")

            await asyncio.sleep(1)  # Check every second

    async def _execute_job(self, job: CronJob) -> CronJobResult:
        """Execute a cron job."""
        start_time = time.time()

        try:
            # Create agent for this job
            agent = create_agent(
                model=job.model or self.config.get("model", "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free"),
                provider=job.provider or self.config.get("provider"),
                max_turns=job.max_turns,
                profile=self.profile,
                platform="cron",
                chat_type="cron",
                chat_id=job.id,
            )

            # Set fallback providers
            if job.fallback_providers:
                agent.config.fallback_providers = job.fallback_providers

            # Set toolsets
            if job.toolsets:
                agent.config.toolsets = job.toolsets

            # Run the job
            result = agent.run_conversation(job.prompt)

            # Update job
            job.last_run = time.time()
            job.run_count += 1
            job.last_result = result
            job.last_error = None

            # Calculate next run
            self._calculate_next_run(job)
            self._save_jobs()

            # Deliver result if configured
            if job.deliver and self.gateway:
                await self._deliver_result(job, result)

            duration = time.time() - start_time

            return CronJobResult(
                job_id=job.id,
                success=True,
                result=result,
                started_at=start_time,
                completed_at=time.time(),
                duration=duration,
            )

        except Exception as e:
            job.last_run = time.time()
            job.last_error = str(e)
            self._calculate_next_run(job)
            self._save_jobs()

            duration = time.time() - start_time

            return CronJobResult(
                job_id=job.id,
                success=False,
                error=str(e),
                started_at=start_time,
                completed_at=time.time(),
                duration=duration,
            )
        finally:
            if job.id in self._running_jobs:
                del self._running_jobs[job.id]

    async def _deliver_result(self, job: CronJob, result: str) -> None:
        """Deliver job result to configured destination."""
        if not self.gateway:
            return

        platform = job.deliver.get("platform")
        chat_type = job.deliver.get("chat_type", "private")
        chat_id = job.deliver.get("chat_id")

        if platform and chat_id:
            message = f"📅 **Cron Job: {job.name}**\n\n{result}"
            await self.gateway.deliver_to_home(platform, message)

    def get_status(self) -> dict:
        """Get cron system status."""
        return {
            "total_jobs": len(self.jobs),
            "enabled_jobs": sum(1 for j in self.jobs.values() if j.enabled),
            "running_jobs": len(self._running_jobs),
            "jobs": [
                {
                    "id": j.id,
                    "name": j.name,
                    "enabled": j.enabled,
                    "schedule": j.schedule,
                    "schedule_type": j.schedule_type.value,
                    "next_run": j.next_run,
                    "last_run": j.last_run,
                    "run_count": j.run_count,
                    "last_error": j.last_error,
                }
                for j in self.jobs.values()
            ],
        }


# =============================================================================
# Cron CLI Commands
# =============================================================================

_cron_manager: CronManager | None = None


def get_cron_manager(profile: str = "default", gateway: GatewayRunner = None) -> CronManager:
    global _cron_manager
    if _cron_manager is None:
        _cron_manager = CronManager(profile=profile, gateway=gateway)
    return _cron_manager


def cron_add(
    name: str,
    schedule: str,
    prompt: str,
    schedule_type: str = "cron",
    model: str = None,
    provider: str = None,
    toolsets: str = None,
    skills: str = None,
    max_turns: int = 500,
) -> str:
    """Add a cron job."""
    manager = get_cron_manager()

    stype = CronScheduleType(schedule_type)
    toolsets = toolsets.split(",") if toolsets else []
    skills_list = skills.split(",") if skills else []

    job_id = manager.add_job(
        name=name,
        schedule=schedule,
        prompt=prompt,
        schedule_type=stype,
        model=model,
        provider=provider,
        toolsets=toolsets,
        skills=skills_list,
        max_turns=max_turns,
    )

    print(f"Added cron job: {job_id} ({name})")
    return job_id


def cron_remove(job_id: str) -> bool:
    """Remove a cron job."""
    manager = get_cron_manager()
    if manager.remove_job(job_id):
        print(f"Removed cron job: {job_id}")
        return True
    else:
        print(f"Job not found: {job_id}")
        return False


def cron_list() -> list[dict]:
    """List all cron jobs."""
    manager = get_cron_manager()
    return [
        {
            "id": j.id,
            "name": j.name,
            "enabled": j.enabled,
            "schedule": j.schedule,
            "schedule_type": j.schedule_type.value,
            "next_run": j.next_run,
            "last_run": j.last_run,
            "run_count": j.run_count,
            "last_error": j.last_error,
        }
        for j in manager.list_jobs()
    ]


def cron_enable(job_id: str, enabled: bool = True) -> bool:
    """Enable or disable a cron job."""
    manager = get_cron_manager()
    if manager.enable_job(job_id, enabled):
        print(f"Job {job_id} {'enabled' if enabled else 'disabled'}")
        return True
    else:
        print(f"Job not found: {job_id}")
        return False


def cron_status() -> dict:
    """Get cron system status."""
    manager = get_cron_manager()
    return manager.get_status()


async def cron_start(profile: str = "default", gateway: GatewayRunner = None) -> None:
    """Start the cron scheduler."""
    global _cron_manager
    _cron_manager = CronManager(profile=profile, gateway=gateway)
    await _cron_manager.start()


async def cron_stop() -> None:
    """Stop the cron scheduler."""
    global _cron_manager
    if _cron_manager:
        await _cron_manager.stop()
        _cron_manager = None
