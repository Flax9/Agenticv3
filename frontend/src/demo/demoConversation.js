// Skrip percakapan untuk mode demo dan balasan chat simulasi.
// Balasan simulasi dipakai sampai endpoint /api/chat/stream tersedia (masterplan Fase 4).
// Teks memakai format aman: **tebal** dan `kode` (dirender oleh RichText, bukan innerHTML).
import { formatRupiah } from '../services/format'
import { DEMO_ATTACHMENT } from './demoData'

export function demoOpening(mode, data) {
  switch (mode) {
    case 'tender':
      return {
        user: {
          text: `Tolong buatkan Dokumen Tender lengkap untuk ${data.nama_pengadaan}. Berikut berkas BoQ acuan.`,
          attachment: DEMO_ATTACHMENT.tender,
        },
        ai: {
          text: `Saya telah memindai berkas \`${DEMO_ATTACHMENT.tender.name}\` (data contoh).`,
          reasoning: [
            'Ditemukan 14 rincian item pekerjaan overhaul tangki bahan bakar minyak.',
            'Mengaplikasikan formula Keuntungan & Risiko (K&R) sebesar 8% standar Regional Kalimantan.',
            'Merujuk kualifikasi CSMS Tinggi (Passing grade 70) sesuai TKO B3.2.4-03.',
          ],
          extractionCard: true,
          artifact: { icon: '📄', title: 'Draft Dokumen Tender Balikpapan v2.0', sub: 'Naskah Resmi Pertamina · IKPP 40 Poin & Kontrak' },
          tail: 'Periksa parameter di atas, lalu tekan **Terapkan** untuk menyusun draf di kanvas.',
        },
      }
    case 'rks':
      return {
        user: {
          text: `Tolong susunkan draf RKS untuk ${data.jenis_pekerjaan} di ${data.lokasi}.`,
          attachment: DEMO_ATTACHMENT.rks,
        },
        ai: {
          tool: {
            title: 'RAG Retrieval: Collection `rks_kb` (Qdrant)',
            lines: [
              'Mengambil 5 bab standar spesifikasi teknis tangki dan perpipaan.',
              'Standar K3 CSMS Kategori HIGH (Passing grade ≥ 70) disuntikkan pada Bab IV.',
              '3 dokumen acuan terkait fuel terminal Balikpapan berhasil disinkronisasi.',
            ],
          },
          text: `Draf RKS telah disusun lengkap sebanyak **${data.bab_count} Bab Teknis** beserta Lembar Pengesahan dan Matriks CSMS.`,
          artifact: { icon: '📋', title: 'Spesifikasi Teknis RKS (Bab I - V)', sub: 'Dokumen Rencana Kerja & Syarat Siap Cetak' },
        },
      }
    case 'contract':
      return {
        user: {
          text: `Tolong susunkan Rancangan Kontrak Definitif untuk ${data.nama_pekerjaan}. Pemenang tender: ${data.nama_vendor}.`,
        },
        ai: {
          tool: {
            title: 'Legal Drafting: Standar 20 Pasal Kontrak Pemborongan Mandiri',
            lines: [
              'Pasal 1 s.d. 20 terkompilasi sesuai format hukum korporat Pertamina.',
              'NPWP vendor dan rekening bank terverifikasi.',
              'Denda keterlambatan 1 permil per hari (maks 5%) otomatis diset pada Pasal 14.',
            ],
          },
          text: `Naskah Kontrak Definitif 20 Pasal telah disusun dengan nilai **${formatRupiah(data.nilai_kontrak)}** dan durasi **${data.durasi_hari} hari kalender**.`,
          artifact: { icon: '📝', title: 'Naskah Rancangan Kontrak (20 Pasal)', sub: 'Perjanjian Pemborongan Pekerjaan Definitif' },
        },
      }
    case 'amendment':
      return {
        user: {
          text: `Tolong susunkan draf Addendum untuk kontrak ${data.nomor_kontrak_asal} karena ada penambahan nilai dan volume pekerjaan.`,
        },
        ai: {
          tool: {
            title: 'Legal Drafting: Addendum Kontrak & Tabel Komparasi Klausul',
            lines: [
              'Merumuskan konsideran Menimbang, Mengingat, dan Memperhatikan.',
              `Menyusun matriks perubahan nilai kontrak dari ${formatRupiah(data.nilai_kontrak_asal)} menjadi ${formatRupiah(data.nilai_kontrak_baru)}.`,
              'Menyiapkan pasal peralihan dan keabsahan addendum.',
            ],
          },
          text: 'Draft Addendum telah dibuat lengkap dengan konsideran dan tabel komparasi kondisi lama vs baru.',
          artifact: { icon: '📎', title: 'Draft Addendum Kontrak (Lama vs Baru)', sub: 'Perubahan Nilai Kontrak & Perpanjangan Waktu' },
        },
      }
    default:
      return null
  }
}

// Balasan berbasis kata kunci. Mengembalikan { text, update?, tab? }
// `update.value` boleh berupa fungsi (data paket aktif) => nilai baru
export function simulatedReply(userText, mode) {
  const lower = userText.toLowerCase()

  if (lower.includes('pemeliharaan') && (mode === 'tender' || mode === 'contract')) {
    return {
      update: { key: mode === 'tender' ? 'masa_pemeliharaan_hari' : 'masa_pemeliharaan', value: 180 },
      text: 'Baik, saya telah memperbarui **Masa Pemeliharaan** menjadi **180 (seratus delapan puluh) hari kalender** pada dokumen canvas.',
    }
  }
  if (mode === 'contract' && lower.includes('vendor')) {
    return {
      update: { key: 'nama_vendor', value: 'PT Contoh Energi Utama' },
      text: 'Pihak Kedua (vendor) telah diganti menjadi **PT Contoh Energi Utama** pada bagian Para Pihak.',
    }
  }
  if (mode === 'contract' && lower.includes('nilai kontrak')) {
    return {
      update: { key: 'nilai_kontrak', value: 9500000000 },
      text: `Nilai kontrak pada Pasal 3 telah diubah menjadi **${formatRupiah(9500000000)}**.`,
    }
  }
  if (mode === 'amendment' && lower.includes('12%')) {
    return {
      update: { key: 'nilai_kontrak_baru', value: (d) => Math.round(d.nilai_kontrak_asal * 1.12) },
      text: 'Nilai kontrak baru pada tabel komparasi telah disesuaikan menjadi **+12%** dari nilai kontrak asal.',
    }
  }
  if (mode === 'tender' && lower.includes('jaminan')) {
    return {
      update: { key: 'jaminan_pelaksanaan_persen', value: 5 },
      text: 'Ketentuan **Jaminan Pelaksanaan sebesar 5% dari Nilai Kontrak** telah diterapkan pada Butir 8 IKPP. Jaminan wajib diterbitkan oleh Bank BUMN atau Bank Swasta Devisa Nasional.',
    }
  }
  if (lower.includes('skor') || lower.includes('kepatuhan') || lower.includes('stk')) {
    return {
      tab: 'checklistTab',
      text: 'Saya telah membuka tab **Checklist STK Mandatory Pra-Tender** pada kanvas.',
    }
  }
  if (lower.includes('hps') || lower.includes('biaya') || lower.includes('matriks') || lower.includes('komparasi')) {
    return {
      tab: 'matrixTab',
      text: 'Saya telah mengalihkan kanvas ke tab **Matriks** untuk memeriksa rinciannya.',
    }
  }
  return {
    text: `Instruksi Anda sudah saya catat: "${userText}". Balasan AI penuh akan tersedia setelah endpoint chat backend aktif.`,
  }
}
