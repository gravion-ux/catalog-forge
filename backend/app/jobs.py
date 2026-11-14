"""Background jobs.

A crawl takes minutes, so it runs as an asyncio task while the admin panel
polls the ``crawl_runs`` table for its progress.
"""

from __future__ import annotations

import asyncio

from app.catalog.crawls import create_crawl_run
from app.config import Settings
from app.crawler.fetcher import Fetcher
from app.crawler.runner import run_crawl
from app.db import session


class CrawlJobs:
    """Starts crawls and keeps the tasks that are running."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._tasks: dict[int, asyncio.Task[None]] = {}

    async def start(self, url: str) -> int:
        """Open a crawl run and start it in the background.

        Returns the id of the run, which is ready to be polled straight away.
        """
        with session(self.settings.database_path) as connection:
            run_id = create_crawl_run(connection, url)

        task = asyncio.create_task(self._run(run_id, url))
        self._tasks[run_id] = task
        task.add_done_callback(lambda finished: self._tasks.pop(run_id, None))
        return run_id

    def is_running(self, run_id: int) -> bool:
        """True while the crawl of this run is still going."""
        task = self._tasks.get(run_id)
        return task is not None and not task.done()

    async def _run(self, run_id: int, url: str) -> None:
        fetcher = Fetcher(
            user_agent=self.settings.crawler_user_agent,
            delay_seconds=self.settings.crawler_delay_seconds,
            max_concurrency=self.settings.crawler_max_concurrency,
            timeout_seconds=self.settings.crawler_timeout_seconds,
            max_pages=self.settings.crawler_max_pages,
            allow_private=self.settings.allow_private_targets,
        )
        try:
            with session(self.settings.database_path) as connection:
                await run_crawl(
                    connection,
                    fetcher,
                    url,
                    media_dir=self.settings.media_dir,
                    run_id=run_id,
                )
        except Exception:  # noqa: BLE001 - the run row records the failure
            pass
        finally:
            await fetcher.aclose()
