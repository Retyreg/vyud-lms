export const storage = {
  getOrgId: (): number | null => {
    const v = localStorage.getItem('vyud_org_id');
    return v ? Number(v) : null;
  },
  setOrgId: (id: number) => localStorage.setItem('vyud_org_id', String(id)),

  getOrgName: (): string | null => localStorage.getItem('vyud_org_name'),
  setOrgName: (name: string) => localStorage.setItem('vyud_org_name', name),

  getUserKey: (): string => localStorage.getItem('vyud_user_key') ?? '',
  setUserKey: (key: string) => localStorage.setItem('vyud_user_key', key),

  clear: () => {
    localStorage.removeItem('vyud_org_id');
    localStorage.removeItem('vyud_org_name');
    localStorage.removeItem('vyud_user_key');
  },
};
