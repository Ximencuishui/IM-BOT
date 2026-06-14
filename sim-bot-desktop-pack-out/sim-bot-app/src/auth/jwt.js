import crypto from 'crypto';

export function signToken(payload, secret, ttlSec = 86400) {
  const body = { ...payload, exp: Math.floor(Date.now() / 1000) + ttlSec };
  const payloadB64 = Buffer.from(JSON.stringify(body), 'utf8').toString('base64url');
  const sig = crypto.createHmac('sha256', secret).update(payloadB64).digest('base64url');
  return `${payloadB64}.${sig}`;
}

export function verifyToken(token, secret) {
  try {
    const [payloadB64, sig] = String(token).split('.');
    if (!payloadB64 || !sig) return null;
    const expect = crypto.createHmac('sha256', secret).update(payloadB64).digest('base64url');
    const a = Buffer.from(sig);
    const b = Buffer.from(expect);
    if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null;
    const body = JSON.parse(Buffer.from(payloadB64, 'base64url').toString('utf8'));
    if (body.exp && body.exp < Math.floor(Date.now() / 1000)) return null;
    return body;
  } catch {
    return null;
  }
}
