# VYUD Demo SOP Library

Набор из 15 SOP в 5 индустриальных сегментах, по 2 языка каждый (RU + EN) = 30 JSON-файлов.

Используется для seed-данных в demo-режиме `lms.vyud.online`: потенциальный клиент регистрируется, выбирает свой сегмент, получает 3 готовых SOP с квизами, чеклистами и KPI.

## Структура

```
vyud-demo-sops/
├── index.json                            # Манифест всех SOP (для seed.py)
├── README.md                              # Этот файл
├── cafe_restaurant/
│   ├── 01_barista_onboarding_{ru,en}.json
│   ├── 02_guest_complaints_{ru,en}.json
│   └── 03_shift_closing_{ru,en}.json
├── hotel/
│   ├── 01_guest_checkin_{ru,en}.json
│   ├── 02_housekeeping_{ru,en}.json
│   └── 03_reception_complaints_{ru,en}.json
├── retail/
│   ├── 01_store_opening_{ru,en}.json
│   ├── 02_returns_{ru,en}.json
│   └── 03_loss_prevention_{ru,en}.json
├── fmcg/
│   ├── 01_store_visit_{ru,en}.json
│   ├── 02_planogram_{ru,en}.json
│   └── 03_objection_handling_{ru,en}.json
└── warehouse/
    ├── 01_receiving_{ru,en}.json
    ├── 02_picking_{ru,en}.json
    └── 03_forklift_safety_{ru,en}.json
```

## Схема файла

Все 30 файлов следуют одной схеме:

```json
{
  "id": "cafe-barista-onboarding",
  "segment": "cafe_restaurant",
  "title": "...",
  "description": "...",
  "estimated_duration_min": 25,
  "language": "ru",
  "steps": [
    {
      "order": 1,
      "title": "...",
      "content": "...",
      "key_takeaway": "..."
    }
  ],
  "quiz": [
    {
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "correct_index": 2,
      "explanation": "..."
    }
  ],
  "manager_checklist": ["...", "..."],
  "kpi": [
    {
      "metric": "...",
      "target": "...",
      "how_to_measure": "..."
    }
  ]
}
```

### Ключевые поля

- **`id`** — стабильный идентификатор, одинаковый для RU и EN версий. Используй для связи переводов в БД.
- **`segment`** — один из 5 enum-значений. Маппится на `demo_user.industry` при регистрации.
- **`steps[].key_takeaway`** — готовый материал для SM-2 карточек знаний в LMS.
- **`quiz[].correct_index`** — 0-based индекс правильного ответа в массиве `options`.
- **`kpi[]`** — для дашборда менеджера и для AI-агента, который будет предлагать метрики на вашем реальном SOP.

## Параметры генерации

- **Объём**: короткий формат (5-7 шагов, ~300 слов) — для быстрого демо.
- **Структура**: шаги + квиз (5 вопросов) + чеклист менеджера + KPI с методикой замера.
- **Языки**: RU + EN. EN — не прямой перевод, а адаптация под международные стандарты (доллары, °F в скобках, термины Marriott/OSHA/FIFO).

## Как использовать в `seed.py`

```python
# backend/app/demo/seed.py
import json
from pathlib import Path

SOP_LIBRARY = Path(__file__).parent / "sops"

def seed_demo_user_sops(db, user: DemoUser):
    """Seed 3 SOPs matching the demo user's industry."""
    with open(SOP_LIBRARY / "index.json") as f:
        manifest = json.load(f)
    
    segment = user.industry  # e.g., "cafe_restaurant"
    lang = user.language or "ru"
    
    for sop_meta in manifest["segments"][segment]["sops"]:
        sop_id = sop_meta["id"]
        # Load the file matching this user's language
        file_path = SOP_LIBRARY / segment / f"*_{lang}.json"
        # ... create SOP, SOPStep, SOPQuiz rows ...
```

## Лицензия

Internal VYUD asset. Не распространять публично без согласования.
