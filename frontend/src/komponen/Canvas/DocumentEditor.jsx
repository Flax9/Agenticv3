import { formatRupiah, percentChange } from '../../services/format'
import { useAppStore } from '../../services/useAppStore'

// Sel yang ditandai kuning sesaat setelah field-nya diubah lewat chat
function Cell({ field, children, ...props }) {
  const highlighted = useAppStore((s) => s.highlight?.key === field)
  return (
    <td {...props} className={`${props.className ?? ''} ${highlighted ? 'highlight-change' : ''}`}>
      {children}
    </td>
  )
}

function Sheet({ title, unit, stamp, heading, subHeading, number, children }) {
  return (
    <article className="relative mb-8 min-h-[900px] rounded border border-pertamina-gray-300 bg-white px-6 py-8 shadow-sheet sm:px-14 sm:py-12">
      <header className="mb-7 flex items-start justify-between gap-4 border-b-2 border-pertamina-navy pb-4">
        <div>
          <div className="text-[15px] font-extrabold uppercase tracking-wide text-pertamina-navy">{title}</div>
          <div className="mt-0.5 text-[11px] font-semibold text-pertamina-gray-500">{unit}</div>
        </div>
        <div className="shrink-0 rounded-md border-[1.5px] border-pertamina-red px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-widest text-pertamina-red">
          {stamp}
        </div>
      </header>
      <div className="mb-9 mt-6 text-center">
        <div className="mb-1.5 text-lg font-extrabold uppercase text-pertamina-navy">{heading}</div>
        <div className="mx-auto max-w-[620px] text-sm font-bold uppercase leading-snug text-pertamina-gray-900">
          {subHeading}
        </div>
        <div className="mt-2.5 inline-block rounded-md bg-pertamina-gray-100 px-3 py-1 font-mono text-xs font-semibold text-pertamina-gray-700">
          {number}
        </div>
      </div>
      {children}
    </article>
  )
}

function TenderDocument({ d }) {
  const rows = [
    ['Nama Pengadaan', d.nama_pengadaan],
    ['Pejabat Berwenang', d.pejabat_berwenang],
    ['Pengawas Pekerjaan', d.pengawas_pekerjaan],
    ['Jenis Kontrak', d.jenis_kontrak],
    ['Metode Pemenuhan', d.metode_pemenuhan],
  ]
  return (
    <Sheet
      title="PT PERTAMINA PATRA NIAGA"
      unit="REGIONAL KALIMANTAN — FUNGSI PROCUREMENT"
      stamp="Confidential / Rahasia"
      heading="Dokumen Tender (DT) — Versi 2.0"
      subHeading={d.nama_pengadaan}
      number={`Nomor: ${d.nomor_tender ?? '—'}`}
    >
      <div className="doc-section-title">Bagian A: Bab I — Ketentuan Khusus Instruksi Kepada Peserta Pengadaan (IKPP)</div>
      <table className="doc-table">
        <thead>
          <tr>
            <th className="w-9">NO</th>
            <th className="w-56">BUTIR KETENTUAN</th>
            <th>KETENTUAN KHUSUS PADA PAKET INI</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, value], i) => (
            <tr key={label}>
              <td className="text-center font-semibold">{i + 1}</td>
              <td className="font-semibold">{label}</td>
              <td>{value ?? '—'}</td>
            </tr>
          ))}
          <tr>
            <td className="text-center font-semibold">6</td>
            <td className="font-semibold">Tingkat Risiko CSMS (HSSE)</td>
            <Cell field="resiko_csms">
              <strong>{d.resiko_csms}</strong>
              {d.csms_grade && ` (${d.csms_grade})`}
            </Cell>
          </tr>
          <tr>
            <td className="text-center font-semibold">7</td>
            <td className="font-semibold">Komitmen Minimal TKDN</td>
            <Cell field="tkdn_minimal">
              Minimal <strong>{d.tkdn_minimal} %</strong> (Form A3/A4/A5 Kemenperin)
            </Cell>
          </tr>
          <tr>
            <td className="text-center font-semibold">8</td>
            <td className="font-semibold">Masa Pemeliharaan / Retensi</td>
            <Cell field="masa_pemeliharaan_hari">
              <strong>{d.masa_pemeliharaan_hari} hari kalender</strong> sejak Serah Terima Pertama (BAST-1)
            </Cell>
          </tr>
          <tr>
            <td className="text-center font-semibold">9</td>
            <td className="font-semibold">Jaminan Pelaksanaan</td>
            <Cell field="jaminan_pelaksanaan_persen">
              Sebesar <strong>{d.jaminan_pelaksanaan_persen}%</strong> dari total nilai kontrak
            </Cell>
          </tr>
        </tbody>
      </table>

      <div className="doc-section-title !bg-pertamina-gray-900">Bagian B: Rancangan Kontrak Definitif (20 Pasal)</div>
      <table className="doc-table">
        <thead>
          <tr>
            <th className="w-40">PASAL</th>
            <th>SUBSTANSI PASAL DALAM NASKAH KONTRAK</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="font-bold">Pasal 2: Lingkup Kerja</td>
            <td>{d.lingkup_pekerjaan || d.context_summary || '— (akan diisi dari ringkasan RKS/BoQ)'}</td>
          </tr>
          <tr>
            <td className="font-bold">Pasal 3: Nilai Kontrak</td>
            <Cell field="total_dengan_kr">
              Total nilai kontrak definitif adalah sebesar {formatRupiah(d.total_dengan_kr)} sudah termasuk PPN.
            </Cell>
          </tr>
        </tbody>
      </table>
    </Sheet>
  )
}

function RksDocument({ d }) {
  const bab = [
    ['BAB I', 'UMUM & LATAR BELAKANG', 'Dasar pelaksanaan pengadaan, lokasi, dan ringkasan fasilitas eksisting.'],
    ['BAB II', 'LINGKUP PEKERJAAN', d.detail_pekerjaan],
    ['BAB III', 'SPESIFIKASI TEKNIS & MUTU', 'Standar API 650/653, ASTM A36, pengujian hydrotest dan NDT.'],
    ['BAB IV', 'PERSYARATAN K3L & CSMS', `Kategori Risiko CSMS ${d.resiko_csms} dengan passing grade 70.`],
    ['BAB V', 'JADWAL & SERAH TERIMA', 'Durasi pelaksanaan, inspeksi bersama BAST-1 dan BAST-2.'],
  ]
  return (
    <Sheet
      title={d.nama_perusahaan}
      unit="FUNGSI PEMINTA PENGADAAN (FPP)"
      stamp="RKS Teknis"
      heading="Rencana Kerja dan Syarat-Syarat (RKS)"
      subHeading={d.jenis_pekerjaan}
      number={`Nomor: ${d.nomor_dokumen} | Lokasi: ${d.lokasi}`}
    >
      <div className="doc-section-title">Lembar Pengesahan Dokumen</div>
      <table className="doc-table">
        <thead>
          <tr>
            <th>Fungsi</th>
            <th>Jabatan</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Disusun Oleh</td>
            <td>Junior Engineer Project — FPP</td>
            <td>✅ Selesai</td>
          </tr>
          <tr>
            <td>Diperiksa Oleh</td>
            <td>Sr. Supervisor Maintenance</td>
            <td>✅ Selesai</td>
          </tr>
          <tr>
            <td>Disetujui Oleh</td>
            <td>Region Manager RPD</td>
            <td>⏳ Menunggu TTD</td>
          </tr>
        </tbody>
      </table>

      <div className="doc-section-title">Struktur Bab RKS ({d.bab_count} Bab)</div>
      <table className="doc-table">
        <thead>
          <tr>
            <th className="w-28">BAB</th>
            <th>JUDUL DAN URAIAN SUBSTANSI</th>
          </tr>
        </thead>
        <tbody>
          {bab.map(([no, judul, isi]) => (
            <tr key={no}>
              <td className="font-bold">{no}</td>
              <td>
                <strong>{judul}:</strong> {isi}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Sheet>
  )
}

function ContractDocument({ d }) {
  return (
    <Sheet
      title="PT PERTAMINA PATRA NIAGA"
      unit="PERJANJIAN PEMBORONGAN PEKERJAAN"
      stamp="Definitif"
      heading="Surat Perjanjian (Kontrak)"
      subHeading={d.nama_pekerjaan}
      number={`Nomor Kontrak: ${d.nomor_kontrak}`}
    >
      <div className="doc-section-title">Para Pihak Penandatangan</div>
      <table className="doc-table">
        <tbody>
          <tr>
            <td className="w-40 font-bold">Pihak Pertama:</td>
            <td>
              <strong>PT PERTAMINA PATRA NIAGA</strong> (Diwakili oleh {d.pejabat_ttd_pertamina})
            </td>
          </tr>
          <tr>
            <td className="font-bold">Pihak Kedua (Vendor):</td>
            <Cell field="nama_vendor">
              <strong>{d.nama_vendor}</strong> (NPWP: {d.npwp_vendor})
            </Cell>
          </tr>
        </tbody>
      </table>

      <div className="doc-section-title">Pasal Kunci Perjanjian (20 Pasal Standar)</div>
      <table className="doc-table">
        <thead>
          <tr>
            <th className="w-36">PASAL</th>
            <th>ISI KLAUSUL RESMI</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="font-bold">Pasal 3 (Nilai)</td>
            <Cell field="nilai_kontrak">
              Nilai pekerjaan adalah <strong>{formatRupiah(d.nilai_kontrak)}</strong> termasuk PPN. Jenis Kontrak:{' '}
              {d.jenis_kontrak}.
            </Cell>
          </tr>
          <tr>
            <td className="font-bold">Pasal 4 (Jangka Waktu)</td>
            <Cell field="durasi_hari">
              Jangka waktu pelaksanaan adalah <strong>{d.durasi_hari} hari kalender</strong> sejak diterbitkannya SPMK.
            </Cell>
          </tr>
          <tr>
            <td className="font-bold">Pasal 5 (Pemeliharaan)</td>
            <Cell field="masa_pemeliharaan">
              Masa pemeliharaan ditetapkan selama <strong>{d.masa_pemeliharaan} hari kalender</strong> sejak BAST-1.
              Retensi 5%.
            </Cell>
          </tr>
          <tr>
            <td className="font-bold">Pasal 10 (Sanksi)</td>
            <td>Denda keterlambatan 1‰ (satu per mil) per hari dengan batas maksimal denda 5%.</td>
          </tr>
        </tbody>
      </table>
    </Sheet>
  )
}

function AmendmentDocument({ d }) {
  const change = percentChange(d.nilai_kontrak_asal, d.nilai_kontrak_baru)
  return (
    <Sheet
      title="PT PERTAMINA PATRA NIAGA"
      unit="ADDENDUM PERJANJIAN PEMBORONGAN"
      stamp="Amendemen"
      heading="Surat Amendemen / Addendum Kontrak"
      subHeading={d.judul_pekerjaan}
      number={`Nomor: ${d.nomor_addendum} | Atas Kontrak: ${d.nomor_kontrak_asal}`}
    >
      <div className="doc-section-title">Konsideran Hukum</div>
      <div className="mb-3.5 space-y-1 text-justify text-xs leading-relaxed">
        <p>
          <strong>Menimbang:</strong> Bahwa terdapat penyesuaian volume dan kondisi lapangan pada pelaksanaan pekerjaan.
        </p>
        <p>
          <strong>Mengingat:</strong> Ketentuan Pasal 18 (Perubahan Pekerjaan) pada Kontrak Asal No.{' '}
          {d.nomor_kontrak_asal}.
        </p>
        <p>
          <strong>Memperhatikan:</strong> Berita Acara Rapat Evaluasi Teknis Bersama Tanggal {d.tanggal_amendemen}.
        </p>
      </div>

      <div className="doc-section-title">Tabel Komparasi Perubahan Pasal (Lama vs Baru)</div>
      <table className="doc-table">
        <thead>
          <tr>
            <th className="w-36">PASAL</th>
            <th>KONDISI LAMA (SEBELUM)</th>
            <th>KONDISI BARU (ADDENDUM)</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="font-bold">Pasal 3: Nilai Kontrak</td>
            <td>{formatRupiah(d.nilai_kontrak_asal)}</td>
            <Cell field="nilai_kontrak_baru" className="!bg-emerald-50 font-bold text-emerald-800">
              {formatRupiah(d.nilai_kontrak_baru)}
              {change !== null && ` (${change >= 0 ? '+' : ''}${change.toFixed(1)}%)`}
            </Cell>
          </tr>
          <tr>
            <td className="font-bold">Dasar Justifikasi</td>
            <td colSpan={2}>{d.alasan}</td>
          </tr>
        </tbody>
      </table>
    </Sheet>
  )
}

const TEMPLATES = {
  tender: TenderDocument,
  rks: RksDocument,
  contract: ContractDocument,
  amendment: AmendmentDocument,
}

// Pratinjau naskah resmi per jenis dokumen (penyuntingan per klausul menyusul di Fase 2-3)
export default function DocumentEditor({ mode, data }) {
  const Template = TEMPLATES[mode]
  return Template ? <Template d={data} /> : null
}
