const crypto = require('crypto');
const fs = require('fs/promises');
const path = require('path');

const grpc = require('@grpc/grpc-js');
const { connect, signers } = require('@hyperledger/fabric-gateway');

function peerPortForOrg(orgId) {
  return 7051 + (orgId - 1) * 2000;
}

function orgPaths(rootDir, orgId) {
  const orgRoot = path.join(
    rootDir,
    'organizations',
    'peerOrganizations',
    `org${orgId}.example.com`
  );
  return {
    orgRoot,
    tlsCert: path.join(
      orgRoot,
      'peers',
      `peer0.org${orgId}.example.com`,
      'tls',
      'ca.crt'
    ),
    signCert: path.join(
      orgRoot,
      'users',
      `Admin@org${orgId}.example.com`,
      'msp',
      'signcerts'
    ),
    keyDir: path.join(
      orgRoot,
      'users',
      `Admin@org${orgId}.example.com`,
      'msp',
      'keystore'
    ),
  };
}

async function loadPrivateKey(keyDir) {
  const files = await fs.readdir(keyDir);
  if (!files.length) {
    throw new Error(`missing private key in ${keyDir}`);
  }
  const keyPem = await fs.readFile(path.join(keyDir, files[0]));
  return crypto.createPrivateKey(keyPem);
}

async function loadFirstFile(dirPath, label) {
  const files = await fs.readdir(dirPath);
  if (!files.length) {
    throw new Error(`missing ${label} in ${dirPath}`);
  }
  return fs.readFile(path.join(dirPath, files[0]));
}

async function createOrgGateway(options) {
  const rootDir = path.resolve(options.rootDir);
  const orgId = Number(options.orgId);
  const channel = options.channel;
  const chaincode = options.chaincode;
  const paths = orgPaths(rootDir, orgId);

  const [tlsRootCert, credentials] = await Promise.all([
    fs.readFile(paths.tlsCert),
    loadFirstFile(paths.signCert, 'sign cert'),
  ]);
  const privateKey = await loadPrivateKey(paths.keyDir);

  const peerHost = `peer0.org${orgId}.example.com`;
  const peerEndpoint = options.peerEndpoint || `${peerHost}:${peerPortForOrg(orgId)}`;
  const client = new grpc.Client(
    peerEndpoint,
    grpc.credentials.createSsl(tlsRootCert),
    {
      'grpc.ssl_target_name_override': peerHost,
      'grpc.default_authority': peerHost,
    }
  );

  const gateway = connect({
    client,
    identity: {
      mspId: `Org${orgId}MSP`,
      credentials,
    },
    signer: signers.newPrivateKeySigner(privateKey),
  });

  const network = gateway.getNetwork(channel);
  const contract = network.getContract(chaincode);

  return {
    orgId,
    channel,
    chaincode,
    async submit(fn, args) {
      const normArgs = Array.isArray(args) ? args.map((item) => String(item)) : [];
      return contract.submitTransaction(fn, ...normArgs);
    },
    async evaluate(fn, args) {
      const normArgs = Array.isArray(args) ? args.map((item) => String(item)) : [];
      return contract.evaluateTransaction(fn, ...normArgs);
    },
    close() {
      gateway.close();
      client.close();
    },
  };
}

async function createOrgGateways(options) {
  const orgIds = Array.isArray(options.orgIds) ? options.orgIds : [];
  const out = new Map();
  for (const orgId of orgIds) {
    out.set(orgId, await createOrgGateway({ ...options, orgId }));
  }
  return out;
}

module.exports = {
  createOrgGateway,
  createOrgGateways,
  orgPaths,
  peerPortForOrg,
};

function readStdin() {
  return new Promise((resolve, reject) => {
    const chunks = [];
    process.stdin.on('data', (chunk) => chunks.push(chunk));
    process.stdin.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')));
    process.stdin.on('error', reject);
  });
}

function decodePayload(payload) {
  if (payload == null) {
    return '';
  }
  const text = Buffer.from(payload).toString('utf8').trim();
  if (!text) {
    return '';
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function main() {
  const raw = await readStdin();
  if (!raw.trim()) {
    return;
  }

  const req = JSON.parse(raw);
  const gateway = await createOrgGateway({
    rootDir: process.env.FABRIC_ROOT || path.join(__dirname, '..', 'fabric-samples', 'test-network'),
    orgId: Number(process.env.FABRIC_ORG_ID || '1'),
    channel: process.env.FABRIC_CHANNEL || 'mychannel',
    chaincode: process.env.FABRIC_CHAINCODE || 'auth',
  });

  try {
    const args = Array.isArray(req.args) ? req.args : [];
    const payload = req.submit
      ? await gateway.submit(req.fn, args)
      : await gateway.evaluate(req.fn, args);
    process.stdout.write(JSON.stringify({ ok: true, data: decodePayload(payload) }));
  } catch (err) {
    process.stdout.write(JSON.stringify({ ok: false, err: err && err.message ? err.message : String(err) }));
    process.exitCode = 1;
  } finally {
    gateway.close();
  }
}

if (require.main === module) {
  main().catch((err) => {
    process.stdout.write(JSON.stringify({ ok: false, err: err && err.message ? err.message : String(err) }));
    process.exitCode = 1;
  });
}
