'use client';

import { useState } from 'react';

interface Props {
  inviteCode: string;
  onJoin: (userKey: string) => void;
  onCreate: (name: string, userKey: string) => void;
  onClose: () => void;
}

export function OrgSetupModal({ inviteCode, onJoin, onCreate, onClose }: Props) {
  const [userKey, setUserKey] = useState('');
  const [orgName, setOrgName] = useState('');

  return (
    <div style={{
      position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.4)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200,
    }}>
      <div style={{
        background: 'white', borderRadius: 16, padding: 32,
        width: 360, boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
      }}>
        {inviteCode ? (
          <>
            <h3 style={{ marginTop: 0 }}>Вступить в команду</h3>
            <p style={{ color: '#64748b', fontSize: 14 }}>Введите ваш email чтобы присоединиться</p>
            <input
              value={userKey}
              onChange={e => setUserKey(e.target.value)}
              placeholder="ваш@email.com"
              style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #e2e8f0', marginBottom: 12, boxSizing: 'border-box' }}
            />
            <button
              onClick={() => onJoin(userKey)}
              disabled={!userKey.trim()}
              style={{ width: '100%', padding: 12, background: '#3b82f6', color: 'white', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 15 }}
            >
              Присоединиться
            </button>
          </>
        ) : (
          <>
            <h3 style={{ marginTop: 0 }}>Создать организацию</h3>
            <input
              value={orgName}
              onChange={e => setOrgName(e.target.value)}
              placeholder="Название компании"
              style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #e2e8f0', marginBottom: 8, boxSizing: 'border-box' }}
            />
            <input
              value={userKey}
              onChange={e => setUserKey(e.target.value)}
              placeholder="Ваш email (менеджер)"
              style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #e2e8f0', marginBottom: 12, boxSizing: 'border-box' }}
            />
            <button
              onClick={() => onCreate(orgName, userKey)}
              disabled={!orgName.trim() || !userKey.trim()}
              style={{ width: '100%', padding: 12, background: '#3b82f6', color: 'white', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 15 }}
            >
              Создать
            </button>
          </>
        )}
        <button
          onClick={onClose}
          style={{ width: '100%', marginTop: 8, padding: 10, background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
        >
          Отмена
        </button>
      </div>
    </div>
  );
}
