import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';

import { app, setServerContext } from '../src/server.js';

async function withServer(repository, fn) {
  setServerContext({ repository, authToken: 'test-token' });
  const server = app.listen(0);
  await once(server, 'listening');
  const { port } = server.address();
  try {
    await fn(`http://127.0.0.1:${port}`);
  } finally {
    await new Promise((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
}

function authHeaders() {
  return {
    'Authorization': 'Bearer test-token',
    'Content-Type': 'application/json',
  };
}

test('health endpoint is public', async () => {
  await withServer({}, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/health`);
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), { ok: true, service: 'homelab-vm-provisioner-db' });
  });
});

test('authenticated endpoint rejects missing auth', async () => {
  await withServer({ listUsers: async () => [] }, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/users`);
    assert.equal(response.status, 401);
  });
});

test('vm definition CRUD route works', async () => {
  const repository = {
    upsertVmDefinition: async (payload) => ({ id: 1, ...payload }),
    getVmDefinitionByName: async (vmName) => ({ id: 1, vm_name: vmName, target_host_id: 'host1', config: { vm: { name: vmName } } }),
    listVmDefinitions: async () => ([{ id: 1, vm_name: 'demo', target_host_id: 'host1', config: { vm: { name: 'demo' } } }]),
    deleteVmDefinition: async (vmName) => ({ id: 1, vm_name: vmName }),
  };

  await withServer(repository, async (baseUrl) => {
    let response = await fetch(`${baseUrl}/vm-definitions`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ vm_name: 'demo', target_host_id: 'host1', config: { vm: { name: 'demo' } } }),
    });
    assert.equal(response.status, 201);

    response = await fetch(`${baseUrl}/vm-definitions/by-name/demo`, { headers: authHeaders() });
    assert.equal(response.status, 200);

    response = await fetch(`${baseUrl}/vm-definitions`, { headers: authHeaders() });
    assert.equal(response.status, 200);

    response = await fetch(`${baseUrl}/vm-definitions/by-name/demo`, { method: 'DELETE', headers: authHeaders() });
    assert.equal(response.status, 200);
  });
});

test('atomic vm definition plus job route works', async () => {
  const repository = {
    upsertVmDefinitionAndEnqueueJob: async () => ({
      vmDefinition: { id: 7, vm_name: 'demo' },
      job: { id: 11, status: 'queued' },
    }),
  };

  await withServer(repository, async (baseUrl) => {
    const response = await fetch(`${baseUrl}/vm-definition-jobs`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        vmDefinition: { vm_name: 'demo', target_host_id: 'host1', config: { vm: { name: 'demo' } } },
        jobType: 'provision_vm',
        jobPayload: { vmName: 'demo' },
      }),
    });
    assert.equal(response.status, 201);
    const payload = await response.json();
    assert.equal(payload.vmDefinition.id, 7);
    assert.equal(payload.job.id, 11);
  });
});

test('runtime state and snapshot routes work', async () => {
  const repository = {
    upsertVmRuntimeState: async (vmName, state) => ({ vm_name: vmName, state }),
    getVmRuntimeState: async (vmName) => ({ vm_name: vmName, state: { status: 'running' } }),
    listVmRuntimeStates: async () => ([{ vm_name: 'demo', state: { status: 'running' } }]),
    deleteVmRuntimeState: async (vmName) => ({ vm_name: vmName, state: {} }),
    upsertVmSnapshot: async (vmName, snapshotId, metadata) => ({ vm_name: vmName, snapshot_id: snapshotId, metadata }),
    getVmSnapshot: async (vmName, snapshotId) => ({ vm_name: vmName, snapshot_id: snapshotId, metadata: {} }),
    listVmSnapshots: async () => ([{ vm_name: 'demo', snapshot_id: 'snap-1', metadata: {} }]),
    deleteVmSnapshot: async (vmName, snapshotId) => ({ vm_name: vmName, snapshot_id: snapshotId, metadata: {} }),
  };

  await withServer(repository, async (baseUrl) => {
    let response = await fetch(`${baseUrl}/vm-runtime-state/demo`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ state: { status: 'running' } }),
    });
    assert.equal(response.status, 201);

    response = await fetch(`${baseUrl}/vm-runtime-state/demo`, { headers: authHeaders() });
    assert.equal(response.status, 200);

    response = await fetch(`${baseUrl}/vm-snapshots/demo/snap-1`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ metadata: { artifact_manifest: {} } }),
    });
    assert.equal(response.status, 201);

    response = await fetch(`${baseUrl}/vm-snapshots/demo`, { headers: authHeaders() });
    assert.equal(response.status, 200);
  });
});
