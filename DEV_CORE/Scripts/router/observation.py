"""Optional Router lifespan ownership; no environment-based activation."""
from contextlib import asynccontextmanager


@asynccontextmanager
async def observation_lifespan(app):
    factory = getattr(app.state, 'observation_factory', None)
    if factory is None:
        yield
        return
    if any(getattr(app.state, key, None) is not None for key in
           ('generation_observer', 'generation_event_factory')):
        raise RuntimeError('Observation dependencies already installed')
    observer, event_factory = factory(app)
    worker = observer.worker
    if worker.snapshot()['running'] or worker.exporter.busy or worker.exporter.closed:
        raise RuntimeError('Observation factory must return a fresh worker')
    try:
        if not callable(event_factory):
            raise ValueError('Observation event factory must be callable')
        worker.start()
        app.state.generation_observer = observer
        app.state.generation_event_factory = event_factory
        yield
    finally:
        # Timeout means drainage is still tracked, not a successful shutdown.
        # Do not leave the lifespan (and destroy its loop) until closure.
        while not await worker.aclose():
            if not worker.snapshot()['running']:
                # The task may have finished just after the wait timed out.
                # Read its result instead of treating that race as failure.
                if not await worker.aclose():
                    raise RuntimeError('Observation exporter closure failed')
                break
        for key, value in (('generation_observer', observer),
                           ('generation_event_factory', event_factory)):
            if hasattr(app.state, key) and getattr(app.state, key) is value:
                delattr(app.state, key)
