import { PrintButton } from './PrintButton';

interface CertData {
  cert_token: string;
  user_key: string;
  sop_title: string;
  org_name: string;
  score: number | null;
  max_score: number | null;
  issued_at: string | null;
}

async function fetchCert(token: string): Promise<CertData | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://38.180.229.254:8000';
  try {
    const res = await fetch(`${apiUrl}/api/cert/${token}`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function CertPage({ params }: { params: { token: string } }) {
  const cert = await fetchCert(params.token);
  const certUrl = `https://lms.vyud.online/cert/${params.token}`;

  if (!cert) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#F8FAFC', fontFamily: 'Inter, system-ui, sans-serif',
      }}>
        <div style={{ textAlign: 'center', padding: 32 }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>🔍</div>
          <h1 style={{ fontSize: 20, color: '#0F172A', margin: '0 0 8px' }}>Сертификат не найден</h1>
          <p style={{ color: '#6B7280', fontSize: 14 }}>Проверьте ссылку или обратитесь к менеджеру.</p>
        </div>
      </div>
    );
  }

  const issuedDate = cert.issued_at
    ? new Date(cert.issued_at).toLocaleDateString('ru', { day: 'numeric', month: 'long', year: 'numeric' })
    : '—';

  return (
    <>
      <style>{`
        @media print {
          body { margin: 0; background: white; }
          .no-print { display: none !important; }
          .cert-sheet { box-shadow: none !important; margin: 0 !important; border-radius: 0 !important; }
        }
      `}</style>

      <div style={{
        minHeight: '100vh', background: '#F1F5F9',
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        padding: '32px 16px', fontFamily: 'Inter, system-ui, sans-serif',
      }}>
        {/* Toolbar */}
        <div className="no-print" style={{
          width: '100%', maxWidth: 640, display: 'flex',
          justifyContent: 'space-between', alignItems: 'center', marginBottom: 20,
        }}>
          <a href="/" style={{ fontSize: 13, color: '#4F46E5', textDecoration: 'none', fontWeight: 600 }}>
            ← VYUD LMS
          </a>
          <PrintButton />
        </div>

        {/* Certificate sheet */}
        <div className="cert-sheet" style={{
          background: 'white', width: '100%', maxWidth: 640,
          borderRadius: 16, padding: '48px 40px',
          border: '2px solid #4F46E5',
          boxShadow: '0 10px 40px rgba(79,70,229,0.12)',
        }}>
          {/* Header */}
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <div style={{
              fontSize: 28, fontWeight: 900, color: '#4F46E5',
              letterSpacing: '-0.5px', marginBottom: 4,
            }}>
              VYUD
            </div>
            <div style={{ fontSize: 11, color: '#6B7280', letterSpacing: 2, textTransform: 'uppercase' }}>
              Frontline Training Platform
            </div>
          </div>

          {/* Divider */}
          <div style={{ borderTop: '1px solid #E0E7FF', marginBottom: 32 }} />

          {/* Title */}
          <div style={{ textAlign: 'center', marginBottom: 32 }}>
            <div style={{ fontSize: 13, color: '#6B7280', marginBottom: 8, letterSpacing: 1, textTransform: 'uppercase' }}>
              Сертификат о прохождении
            </div>
            <h1 style={{
              fontSize: 22, fontWeight: 800, color: '#0F172A',
              margin: 0, lineHeight: 1.3,
            }}>
              {cert.sop_title}
            </h1>
          </div>

          {/* Details */}
          <div style={{
            background: '#F8FAFF', borderRadius: 12, padding: '20px 24px',
            display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 28,
          }}>
            <DetailRow label="Организация" value={cert.org_name} />
            <DetailRow label="Выдан" value={issuedDate} />
            {cert.score !== null && cert.max_score !== null && cert.max_score > 0 && (
              <DetailRow label="Результат теста" value={`${cert.score} / ${cert.max_score}`} />
            )}
          </div>

          {/* QR + token */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 20, justifyContent: 'center' }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=${encodeURIComponent(certUrl)}`}
              alt="QR-код сертификата"
              width={100}
              height={100}
              style={{ borderRadius: 8, border: '1px solid #E5E7EB' }}
            />
            <div>
              <div style={{ fontSize: 11, color: '#6B7280', marginBottom: 4 }}>ID сертификата</div>
              <div style={{ fontSize: 12, fontFamily: 'monospace', color: '#374151', wordBreak: 'break-all' }}>
                {cert.cert_token}
              </div>
              <div style={{ fontSize: 11, color: '#9CA3AF', marginTop: 6 }}>
                Проверить: lms.vyud.online/cert/…
              </div>
            </div>
          </div>

          {/* Footer */}
          <div style={{ borderTop: '1px solid #E0E7FF', marginTop: 28, paddingTop: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 11, color: '#9CA3AF' }}>
              Сертификат выдан автоматически платформой VYUD Frontline
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 16 }}>
      <span style={{ fontSize: 13, color: '#6B7280', flexShrink: 0 }}>{label}</span>
      <span style={{ fontSize: 14, fontWeight: 600, color: '#0F172A', textAlign: 'right' }}>{value}</span>
    </div>
  );
}
