# TODO: Fix Honcho/Celery Worker Display Access Issue

## Problem Description
When running the self-operating computer agent through Honcho with curl requests, the agent doesn't perform visible actions on the screen, and logs are not visible in the Honcho terminal. This is because:

1. The Celery worker runs in the background and doesn't have access to the display
2. The worker's output is not directed to the Honcho terminal
3. GUI operations fail silently when there's no display access

## Current Behavior
- API server works correctly and accepts requests
- Celery worker receives tasks but fails with SIGKILL when trying to perform GUI operations
- No visible actions on the screen
- Limited visibility into the agent's progress

## Desired Behavior
- Agent should perform visible actions on the screen when triggered via curl requests
- Logs should be visible in the Honcho terminal
- GUI operations should work correctly

## Potential Solutions to Try

### 1. Fix Display Access for Celery Worker
- Set proper DISPLAY environment variable for the worker process
- Ensure the worker has the necessary permissions to access the display

### 2. Improve Logging Visibility
- Redirect worker logs to stdout so they appear in Honcho
- Add more detailed logging to track agent progress

### 3. Alternative Approaches
- Consider running the worker in a different way that allows display access
- Explore using a different process management approach for the worker

## Commands to Test
```bash
# Start services with Honcho
honcho start

# Send test request
curl -X POST "http://localhost:8000/api/tests" -H "Content-Type: application/json" -d '{"objective": "Open the calculator app and add 2 plus 2"}'

# Check job status
curl -X GET "http://localhost:8000/api/tests/JOB_ID"
```

## Related Files
- `/api/worker.py` - Celery worker implementation
- `/api/main.py` - API server implementation
- `/operate/operate.py` - Main agent logic
- `/operate/utils/logger.py` - Logging utilities