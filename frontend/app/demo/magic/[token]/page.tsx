'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { API_BASE_URL } from '@/lib/api';
import { saveDemoSession } from '@/lib/demo';

export default function MagicCallbackPage() {
  const params = useParams();
  const router = useRouter();
  const token = params?.token as string;

  const [status, setStatus] = useState<'loading' | 'error'>('loading');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (!token) return;

    fetch(`${API_BASE_URL}/api/v1/demo/auth/${token}`)
      .then(async res => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || 'Недействительная ссылка');
        }
        return res.json();
      })
      .then(data => {
        saveDemoSession({
          session_token: data.session_token,
          demo_user_id: data.demo_user_id,
          demo_course_id: data.demo_course_id,
          full_name: data.full_name,
          expires_at: data.expires_at,
        });
        router.replace('/?demo=1');
      })
      .catch((err: unknown) => {
        setErrorMsg(err instanceof Error ? err.message : 'Что-то пошло не так');
        setStatus('error');
      });
  }, [token, router]);

  if (status === 'loading') {
    return (
      <div style={centerStyle}>
        <div style={{ fontSize: 36, marginBottom: 12 }}>🔑</div>
        <p style={{ color: '#475569', fontSize: 15 }}>Входим в демо...</p>
      </div>
    );
  }

  return (
    <div style={centerStyle}>
      <div style={{ fontSize: 36, marginBottom: 12 }}>❌</div>
      <p style={{ color: '#dc2626', fontSize: 15 }}>{errorMsg}</p>
      <a href="/demo" style={{ color: '#4f46e5', fontSize: 13, marginTop: 12 }}>
        Запросить новую ссылку
      </a>
    </div>
  );
}

const centerStyle: React.CSSProperties = {
  minHeight: '100vh',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  fontFamily: 'Inter, system-ui, sans-serif',
};
