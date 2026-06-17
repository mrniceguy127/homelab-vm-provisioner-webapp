import express from 'express';
import { createRepository } from './repository.js';

const PORT = Number.parseInt(process.env.DB_SERVICE_PORT || '3002', 10);
const DATABASE_URL = process.env.DATABASE_URL || 'postgresql://hlvmp:hlvmppass@localhost:5432/hlvmp';
const DB_SERVICE_PASSWORD = process.env.DB_SERVICE_PASSWORD || 'changeme_db_secret';

if (!DATABASE_URL) {
  console.error('Error: DATABASE_URL environment variable is required');
  process.exit(1);
}

if (!DB_SERVICE_PASSWORD) {
  console.error('Error: DB_SERVICE_PASSWORD environment variable is required');
  process.exit(1);
}

const app = express();
app.use(express.json({ limit: '10mb' }));

// Authentication middleware
function authenticate(req, res, next) {
  // Skip auth for health check
  if (req.path === '/health') {
    return next();
  }
  
  const authHeader = req.headers.authorization;
  
  if (!authHeader) {
    return res.status(401).json({ error: 'Missing Authorization header' });
  }
  
  // Support both "Bearer <password>" and just "<password>"
  const token = authHeader.startsWith('Bearer ')
    ? authHeader.slice(7)
    : authHeader;
  
  if (token !== DB_SERVICE_PASSWORD) {
    return res.status(401).json({ error: 'Invalid authorization token' });
  }
  
  next();
}

app.use(authenticate);

let repository = null;

// Initialize repository
async function initializeRepository() {
  try {
    repository = await createRepository(DATABASE_URL);
    console.log('Database repository initialized');
  } catch (error) {
    console.error('Failed to initialize repository:', error.message);
    process.exit(1);
  }
}

// Health check
app.get('/health', (_req, res) => {
  res.json({ ok: true, service: 'homelab-vm-provisioner-db' });
});

// Enqueue job
app.post('/jobs', async (req, res, next) => {
  try {
    const { type, targetHostId, targetVmId, payload, maxAttempts } = req.body;
    
    if (!type || !targetHostId || !payload) {
      return res.status(400).json({
        error: 'Missing required fields: type, targetHostId, payload',
      });
    }
    
    const job = await repository.enqueueJob(type, targetHostId, payload, {
      targetVmId,
      maxAttempts,
    });
    
    res.status(201).json({ job });
  } catch (error) {
    next(error);
  }
});

// List jobs
app.get('/jobs', async (req, res, next) => {
  try {
    const { status, targetHostId, limit } = req.query;
    
    const jobs = await repository.listJobs({
      status,
      targetHostId,
      limit: limit ? Number.parseInt(limit, 10) : undefined,
    });
    
    res.json({ jobs });
  } catch (error) {
    next(error);
  }
});

// Get job by ID
app.get('/jobs/:id', async (req, res, next) => {
  try {
    const jobId = Number.parseInt(req.params.id, 10);
    
    if (Number.isNaN(jobId)) {
      return res.status(400).json({ error: 'Invalid job ID' });
    }
    
    const job = await repository.getJob(jobId);
    
    if (!job) {
      return res.status(404).json({ error: 'Job not found' });
    }
    
    res.json({ job });
  } catch (error) {
    next(error);
  }
});

// Get job events
app.get('/jobs/:id/events', async (req, res, next) => {
  try {
    const jobId = Number.parseInt(req.params.id, 10);
    
    if (Number.isNaN(jobId)) {
      return res.status(400).json({ error: 'Invalid job ID' });
    }
    
    const limit = req.query.limit ? Number.parseInt(req.query.limit, 10) : 100;
    const events = await repository.listJobEvents(jobId, limit);
    
    res.json({ events });
  } catch (error) {
    next(error);
  }
});

// Append job event
app.post('/jobs/:id/events', async (req, res, next) => {
  try {
    const jobId = Number.parseInt(req.params.id, 10);
    
    if (Number.isNaN(jobId)) {
      return res.status(400).json({ error: 'Invalid job ID' });
    }
    
    const { level, message, metadata } = req.body;
    
    if (!level || !message) {
      return res.status(400).json({
        error: 'Missing required fields: level, message',
      });
    }
    
    const event = await repository.appendJobEvent(jobId, level, message, metadata);
    
    res.status(201).json({ event });
  } catch (error) {
    next(error);
  }
});

// Cancel job
app.post('/jobs/:id/cancel', async (req, res, next) => {
  try {
    const jobId = Number.parseInt(req.params.id, 10);
    
    if (Number.isNaN(jobId)) {
      return res.status(400).json({ error: 'Invalid job ID' });
    }
    
    const job = await repository.cancelQueuedJob(jobId);
    res.json({ job });
  } catch (error) {
    if (error.message.includes('not found') || error.message.includes('not in queued state')) {
      return res.status(400).json({ error: error.message });
    }
    next(error);
  }
});

// Claim next job for host
app.post('/jobs/claim', async (req, res, next) => {
  try {
    const { targetHostId, workerId } = req.body;
    
    if (!targetHostId || !workerId) {
      return res.status(400).json({
        error: 'Missing required fields: targetHostId, workerId',
      });
    }
    
    const job = await repository.claimNextJobForHost(targetHostId, workerId);
    
    if (!job) {
      return res.status(404).json({ error: 'No jobs available' });
    }
    
    res.json({ job });
  } catch (error) {
    next(error);
  }
});

// Mark job running
app.post('/jobs/:id/running', async (req, res, next) => {
  try {
    const jobId = Number.parseInt(req.params.id, 10);
    
    if (Number.isNaN(jobId)) {
      return res.status(400).json({ error: 'Invalid job ID' });
    }
    
    const { workerId } = req.body;
    
    if (!workerId) {
      return res.status(400).json({ error: 'Missing required field: workerId' });
    }
    
    const job = await repository.markJobRunning(jobId, workerId);
    res.json({ job });
  } catch (error) {
    next(error);
  }
});

// Mark job succeeded
app.post('/jobs/:id/succeeded', async (req, res, next) => {
  try {
    const jobId = Number.parseInt(req.params.id, 10);
    
    if (Number.isNaN(jobId)) {
      return res.status(400).json({ error: 'Invalid job ID' });
    }
    
    const { result } = req.body;
    
    const job = await repository.markJobSucceeded(jobId, result || {});
    res.json({ job });
  } catch (error) {
    next(error);
  }
});

// Mark job failed
app.post('/jobs/:id/failed', async (req, res, next) => {
  try {
    const jobId = Number.parseInt(req.params.id, 10);
    
    if (Number.isNaN(jobId)) {
      return res.status(400).json({ error: 'Invalid job ID' });
    }
    
    const { error, retriable } = req.body;
    
    if (!error) {
      return res.status(400).json({ error: 'Missing required field: error' });
    }
    
    const job = await repository.markJobFailed(jobId, error, retriable || false);
    res.json({ job });
  } catch (err) {
    next(err);
  }
});

// Acquire resource locks
app.post('/locks/acquire', async (req, res, next) => {
  try {
    const { jobId, workerId, lockKeys, ttlMs } = req.body;
    
    if (!jobId || !workerId || !lockKeys || !Array.isArray(lockKeys)) {
      return res.status(400).json({
        error: 'Missing or invalid required fields: jobId, workerId, lockKeys (array)',
      });
    }
    
    const acquired = await repository.acquireResourceLocks(
      jobId,
      workerId,
      lockKeys,
      ttlMs || 300000
    );
    
    res.json({ acquired });
  } catch (error) {
    next(error);
  }
});

// Release resource locks
app.post('/locks/release', async (req, res, next) => {
  try {
    const { jobId, workerId } = req.body;
    
    if (!jobId) {
      return res.status(400).json({ error: 'Missing required field: jobId' });
    }
    
    const count = await repository.releaseResourceLocks(jobId, workerId);
    res.json({ released: count });
  } catch (error) {
    next(error);
  }
});

// Cleanup expired locks
app.post('/locks/cleanup', async (req, res, next) => {
  try {
    const count = await repository.cleanupExpiredLocks();
    res.json({ cleaned: count });
  } catch (error) {
    next(error);
  }
});

// 404 handler
app.use((_req, res) => {
  res.status(404).json({ error: 'Route not found' });
});

// Error handler
app.use((error, _req, res, _next) => {
  console.error('Error:', error);
  res.status(error.statusCode || 500).json({
    error: error.message || 'Internal server error',
  });
});

// Start server
async function main() {
  await initializeRepository();
  
  app.listen(PORT, () => {
    console.log(`homelab-vm-provisioner-db microservice listening on port ${PORT}`);
  });
}

main().catch((error) => {
  console.error('Failed to start server:', error);
  process.exit(1);
});
