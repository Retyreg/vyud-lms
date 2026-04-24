export default function PricingPage() {
  return (
    <div style={{
      minHeight: '100vh', background: '#F8FAFC',
      fontFamily: 'Inter, system-ui, sans-serif',
      padding: '48px 16px',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
    }}>
      <div style={{ maxWidth: 720, width: '100%' }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: 48 }}>
          <div style={{ fontSize: 28, fontWeight: 900, color: '#4F46E5', marginBottom: 8 }}>VYUD Frontline</div>
          <h1 style={{ fontSize: 32, fontWeight: 800, color: '#0F172A', margin: '0 0 12px' }}>
            Тарифные планы
          </h1>
          <p style={{ color: '#6B7280', fontSize: 16, margin: 0 }}>
            Выберите план, подходящий для вашей команды
          </p>
        </div>

        {/* Plans */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 24, marginBottom: 48 }}>
          {/* Free */}
          <div style={{
            background: 'white', borderRadius: 16, padding: '32px 24px',
            border: '2px solid #E5E7EB',
          }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
              Бесплатно
            </div>
            <div style={{ fontSize: 36, fontWeight: 900, color: '#0F172A', marginBottom: 4 }}>0 ₽</div>
            <div style={{ fontSize: 13, color: '#9CA3AF', marginBottom: 24 }}>навсегда</div>
            <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
              {['1 регламент', '5 сотрудников', 'Шаблоны', 'Квизы + сертификаты'].map(f => (
                <li key={f} style={{ display: 'flex', gap: 8, fontSize: 14, color: '#374151' }}>
                  <span style={{ color: '#10B981' }}>✓</span> {f}
                </li>
              ))}
            </ul>
            <div style={{
              padding: '10px 20px', borderRadius: 10, background: '#F3F4F6',
              color: '#6B7280', fontSize: 14, fontWeight: 600, textAlign: 'center',
            }}>
              Текущий план
            </div>
          </div>

          {/* Starter */}
          <div style={{
            background: 'white', borderRadius: 16, padding: '32px 24px',
            border: '2px solid #4F46E5',
            boxShadow: '0 8px 32px rgba(79,70,229,0.12)',
          }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#4F46E5', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
              Starter
            </div>
            <div style={{ fontSize: 36, fontWeight: 900, color: '#0F172A', marginBottom: 4 }}>5 000 ₽</div>
            <div style={{ fontSize: 13, color: '#9CA3AF', marginBottom: 24 }}>в месяц</div>
            <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
              {['10 регламентов', '25 сотрудников', 'Всё из Free', 'Назначения + дедлайны', 'Дайджест менеджера'].map(f => (
                <li key={f} style={{ display: 'flex', gap: 8, fontSize: 14, color: '#374151' }}>
                  <span style={{ color: '#10B981' }}>✓</span> {f}
                </li>
              ))}
            </ul>
            <a
              href="https://t.me/VyudAI"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'block', padding: '12px 20px', borderRadius: 10,
                background: '#4F46E5', color: 'white', fontSize: 15, fontWeight: 700,
                textDecoration: 'none', textAlign: 'center',
              }}
            >
              Подключить →
            </a>
          </div>

          {/* Team */}
          <div style={{
            background: 'white', borderRadius: 16, padding: '32px 24px',
            border: '2px solid #E5E7EB',
          }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
              Team
            </div>
            <div style={{ fontSize: 36, fontWeight: 900, color: '#0F172A', marginBottom: 4 }}>15 000 ₽</div>
            <div style={{ fontSize: 13, color: '#9CA3AF', marginBottom: 24 }}>в месяц</div>
            <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
              {['Неограниченно регламентов', 'Неограниченно сотрудников', 'Всё из Starter', 'White-label брендинг', 'Приоритетная поддержка'].map(f => (
                <li key={f} style={{ display: 'flex', gap: 8, fontSize: 14, color: '#374151' }}>
                  <span style={{ color: '#10B981' }}>✓</span> {f}
                </li>
              ))}
            </ul>
            <a
              href="https://t.me/VyudAI"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'block', padding: '12px 20px', borderRadius: 10,
                background: '#0F172A', color: 'white', fontSize: 15, fontWeight: 700,
                textDecoration: 'none', textAlign: 'center',
              }}
            >
              Связаться →
            </a>
          </div>
        </div>

        {/* Footer note */}
        <p style={{ textAlign: 'center', color: '#9CA3AF', fontSize: 13 }}>
          Вопросы? Напишите нам в{' '}
          <a href="https://t.me/VyudAI" style={{ color: '#4F46E5' }}>Telegram</a>
        </p>
      </div>
    </div>
  );
}
