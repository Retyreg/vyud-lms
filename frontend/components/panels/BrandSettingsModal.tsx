'use client';

import { useState } from 'react';

interface OrgBrand {
  brand_color: string | null;
  logo_url: string | null;
  bot_username: string | null;
  display_name: string | null;
}

interface Props {
  orgId: number;
  userKey: string;
  orgName: string;
  inviteCode: string;
  initialBrand: OrgBrand;
  onClose: () => void;
  onSaved: (brand: OrgBrand) => void;
}

const PRESET_COLORS = [
  '#3b82f6', '#8b5cf6', '#22c55e', '#f59e0b',
  '#ef4444', '#14b8a6', '#ec4899', '#64748b',
];

export function BrandSettingsModal({
  orgId,
  userKey,
  orgName,
  inviteCode,
  initialBrand,
  onClose,
  onSaved,
}: Props) {
  const [brand, setBrand] = useState<OrgBrand>({ ...initialBrand });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? '';

  const tmaDeepLink = brand.bot_username
    ? `https://t.me/${brand.bot_username.replace(/^@/, '')}?startapp=org_${orgId}`
    : '';

  const inviteUrl = typeof window !== 'undefined'
    ? `${window.location.origin}${window.location.pathname}?invite=${inviteCode}`
    : '';

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(
        `${apiBase}/api/orgs/${orgId}/brand?user_key=${encodeURIComponent(userKey)}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(brand),
        },
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `HTTP ${res.status}`);
      }
      const saved: OrgBrand = await res.json();
      onSaved(saved);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Ошибка сохранения');
    } finally {
      setSaving(false);
    }
  }

  function copyDeepLink() {
    const text = tmaDeepLink || inviteUrl;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  const previewColor = brand.brand_color ?? '#3b82f6';

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 300, padding: 16,
    }}>
      <div style={{
        background: 'white', borderRadius: 16, padding: 24,
        width: '100%', maxWidth: 460, maxHeight: '90vh', overflowY: 'auto',
        boxShadow: '0 8px 32px rgba(0,0,0,0.25)',
      }}>

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h2 style={{ margin: 0, fontSize: 17, color: '#1e293b' }}>🎨 Брендинг</h2>
          <button onClick={onClose} style={btnGhost}>✕</button>
        </div>

        {/* Preview strip */}
        <div style={{
          background: previewColor, borderRadius: 10,
          padding: '12px 16px', marginBottom: 20,
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          {brand.logo_url && (
            <img
              src={brand.logo_url}
              alt="logo"
              style={{ width: 32, height: 32, borderRadius: 6, objectFit: 'cover', background: 'white' }}
              onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          )}
          <span style={{ color: 'white', fontWeight: 600, fontSize: 15 }}>
            {brand.display_name || orgName}
          </span>
        </div>

        {/* Display name */}
        <Field label="Название (в шапке TMA)">
          <input
            value={brand.display_name ?? ''}
            placeholder={orgName}
            onChange={e => setBrand(b => ({ ...b, display_name: e.target.value || null }))}
            style={inputStyle}
          />
        </Field>

        {/* Brand color */}
        <Field label="Основной цвет">
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            {PRESET_COLORS.map(c => (
              <button
                key={c}
                onClick={() => setBrand(b => ({ ...b, brand_color: c }))}
                style={{
                  width: 28, height: 28, borderRadius: '50%', background: c, border: 'none',
                  cursor: 'pointer', outline: brand.brand_color === c ? `3px solid ${c}` : 'none',
                  outlineOffset: 2,
                }}
              />
            ))}
            <input
              type="color"
              value={brand.brand_color ?? '#3b82f6'}
              onChange={e => setBrand(b => ({ ...b, brand_color: e.target.value }))}
              style={{ width: 28, height: 28, border: 'none', borderRadius: '50%', cursor: 'pointer', padding: 0 }}
              title="Свой цвет"
            />
          </div>
        </Field>

        {/* Logo URL */}
        <Field label="URL логотипа">
          <input
            value={brand.logo_url ?? ''}
            placeholder="https://example.com/logo.png"
            onChange={e => setBrand(b => ({ ...b, logo_url: e.target.value || null }))}
            style={inputStyle}
          />
        </Field>

        {/* Bot username */}
        <Field label="Username бота (без @)">
          <input
            value={brand.bot_username ?? ''}
            placeholder="MyCompanyBot"
            onChange={e => setBrand(b => ({ ...b, bot_username: e.target.value || null }))}
            style={inputStyle}
          />
        </Field>

        {/* Deep link */}
        {(tmaDeepLink || inviteUrl) && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 12, color: '#64748b', marginBottom: 6, fontWeight: 600 }}>
              {tmaDeepLink ? 'Ссылка на TMA (для бота)' : 'Инвайт-ссылка'}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <div style={{
                flex: 1, background: '#f8fafc', border: '1px solid #e2e8f0',
                borderRadius: 8, padding: '8px 12px', fontSize: 12, color: '#334155',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {tmaDeepLink || inviteUrl}
              </div>
              <button onClick={copyDeepLink} style={btnBlue}>
                {copied ? '✓ Скопировано' : '📋 Копировать'}
              </button>
            </div>
          </div>
        )}

        {error && (
          <div style={{ color: '#ef4444', fontSize: 12, marginBottom: 12 }}>{error}</div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={btnGhost}>Отмена</button>
          <button onClick={handleSave} disabled={saving} style={{ ...btnBlue, padding: '8px 20px' }}>
            {saving ? '⏳ Сохранение...' : '💾 Сохранить'}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 12, color: '#64748b', marginBottom: 5, fontWeight: 600 }}>{label}</div>
      {children}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px 10px', fontSize: 13,
  border: '1px solid #e2e8f0', borderRadius: 8, outline: 'none',
  color: '#1e293b', background: '#f8fafc', boxSizing: 'border-box',
};

const btnGhost: React.CSSProperties = {
  background: 'none', border: 'none', cursor: 'pointer',
  fontSize: 14, color: '#94a3b8', padding: '4px 8px', borderRadius: 6,
};

const btnBlue: React.CSSProperties = {
  padding: '6px 12px', background: '#dbeafe', border: '1px solid #93c5fd',
  borderRadius: 6, cursor: 'pointer', fontSize: 12, color: '#1d4ed8',
  whiteSpace: 'nowrap',
};
