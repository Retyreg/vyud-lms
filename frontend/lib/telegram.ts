/**
 * Telegram WebApp SDK helpers.
 *
 * Always guard calls with isTMA() — outside Telegram the SDK is absent.
 */

declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        initData: string;
        initDataUnsafe: {
          user?: {
            id: number;
            first_name: string;
            last_name?: string;
            username?: string;
          };
          /** Passed via t.me/bot/app?startapp=<value> — used for invite codes */
          start_param?: string;
        };
        ready(): void;
        expand(): void;
        close(): void;
      };
    };
  }
}

/** Returns true when running inside Telegram Mini App. */
export function isTMA(): boolean {
  return (
    typeof window !== 'undefined' &&
    !!window.Telegram?.WebApp?.initData
  );
}

/** Raw initData string for X-Init-Data header. Empty string outside TMA. */
export function getTelegramInitData(): string {
  return window.Telegram?.WebApp?.initData ?? '';
}

/** Parsed Telegram user from initDataUnsafe. Null outside TMA or if absent. */
export function getTelegramUser() {
  return window.Telegram?.WebApp?.initDataUnsafe?.user ?? null;
}

/**
 * start_param passed via deep link: t.me/bot/app?startapp=<value>.
 * Used to carry invite codes into the Mini App.
 */
export function getTelegramStartParam(): string | undefined {
  return window.Telegram?.WebApp?.initDataUnsafe?.start_param;
}
