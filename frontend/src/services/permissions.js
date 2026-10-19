// Cermin matriks peran masterplan 4.4. Hanya untuk menyembunyikan tombol di UI;
// penegakan sebenarnya ada di backend (require_role).
const PERMISSIONS = {
  draft: ['ADMIN', 'PROCUREMENT', 'FPP'], // sesi chat, ekstraksi, revisi
  generate: ['ADMIN', 'PROCUREMENT', 'FPP', 'APPROVER'], // unduh .docx
  manageKb: ['ADMIN', 'PROCUREMENT'],
}

export const ROLE_LABELS = {
  ADMIN: 'Administrator',
  PROCUREMENT: 'Procurement',
  FPP: 'Fungsi Peminta (FPP)',
  APPROVER: 'Approver',
  AUDITOR: 'Auditor',
}

export function can(user, action) {
  return Boolean(user && PERMISSIONS[action]?.includes(user.role))
}
