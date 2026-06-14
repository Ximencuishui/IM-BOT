import crypto from 'crypto';
import os from 'os';

/** 本机派生密钥（非硬件绑定时可替换为 WMI 机器码） */
export function getMachineSecretKey() {
  const seed = [
    os.hostname(),
    os.userInfo().username,
    process.env.COMPUTERNAME || '',
    process.env.SIMBOT_MACHINE_KEY || 'sim-bot-default-machine-key',
  ].join('|');
  return crypto.createHash('sha256').update(seed, 'utf8').digest();
}

export function computeIntegrityHash(expireData, cipher, secretKey = null) {
  const key = secretKey || getMachineSecretKey();
  const payload = `${String(expireData || '')}${String(cipher || '')}`;
  return crypto.createHmac('sha256', key).update(payload, 'utf8').digest('hex');
}

export function verifyIntegrity(expireData, cipher, savedHash, secretKey = null) {
  if (!savedHash) return false;
  const computed = computeIntegrityHash(expireData, cipher, secretKey);
  return computed === String(savedHash);
}
