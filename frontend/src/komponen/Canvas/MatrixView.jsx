import { formatRupiah, percentChange } from '../../services/format'

function Card({ title, source, children }) {
  return (
    <div className="mb-5 rounded-lg border border-pertamina-gray-200 bg-white p-4 shadow-sm sm:p-[22px]">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 text-sm font-bold text-pertamina-navy">
        <span>{title}</span>
        {source && (
          <span className="rounded-md bg-pertamina-gray-100 px-1.5 py-0.5 font-mono text-[10px] font-normal text-pertamina-gray-500">
            {source}
          </span>
        )}
      </div>
      {children}
    </div>
  )
}

function KpiRow({ items }) {
  return (
    <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
      {items.map(({ label, value, tone }) => (
        <div key={label} className="rounded-lg border border-pertamina-gray-200 bg-pertamina-gray-50 p-3.5 text-center">
          <div className="mb-1 text-[11px] font-semibold text-pertamina-gray-500">{label}</div>
          <div className={`font-mono text-base font-extrabold ${tone ?? 'text-pertamina-navy'}`}>{value}</div>
        </div>
      ))}
    </div>
  )
}

function TenderMatrix({ d }) {
  const kr = d.total_dengan_kr && d.prime_cost ? d.total_dengan_kr - d.prime_cost : null
  const items = d.boq_items ?? []
  return (
    <Card title="Rincian Kalkulasi Harga Perkiraan Sendiri (HPS/OE)" source="TKI C3.2.3-01 Lampiran 3">
      <KpiRow
        items={[
          { label: 'Prime Cost (HPS Riil FPP)', value: formatRupiah(d.prime_cost) },
          { label: `Keuntungan & Risiko (${d.keuntungan_risiko_persen ?? 8}%)`, value: formatRupiah(kr), tone: 'text-amber-600' },
          { label: 'Total HPS Pembulatan', value: formatRupiah(d.total_dengan_kr), tone: 'text-emerald-600' },
        ]}
      />
      {items.length === 0 ? (
        <p className="rounded-md border border-dashed border-pertamina-gray-300 p-3 text-xs text-pertamina-gray-500">
          Rincian item BoQ belum tersedia dari hasil ekstraksi. Total di atas diambil dari rekapitulasi dokumen acuan.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="doc-table">
            <thead>
              <tr>
                <th>No</th>
                <th>Uraian Elemen Biaya</th>
                <th>Volume</th>
                <th>Satuan</th>
                <th>Harga Satuan (IDR)</th>
                <th>Total Biaya (IDR)</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, i) => (
                <tr key={item.uraian}>
                  <td>{i + 1}</td>
                  <td>{item.uraian}</td>
                  <td className="font-mono">{item.volume.toLocaleString('id-ID')}</td>
                  <td>{item.satuan}</td>
                  <td className="font-mono">{item.harga.toLocaleString('id-ID')}</td>
                  <td className="font-mono">{(item.volume * item.harga).toLocaleString('id-ID')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}

function SummaryMatrix({ mode, d }) {
  if (mode === 'amendment') {
    const change = percentChange(d.nilai_kontrak_asal, d.nilai_kontrak_baru)
    return (
      <Card title="Komparasi Nilai Kontrak (Lama vs Baru)" source="Addendum">
        <KpiRow
          items={[
            { label: 'Nilai Kontrak Asal', value: formatRupiah(d.nilai_kontrak_asal) },
            { label: 'Nilai Kontrak Baru', value: formatRupiah(d.nilai_kontrak_baru), tone: 'text-emerald-600' },
            {
              label: 'Perubahan',
              value: change === null ? '—' : `${change >= 0 ? '+' : ''}${change.toFixed(1)}%`,
              tone: 'text-amber-600',
            },
          ]}
        />
      </Card>
    )
  }
  if (mode === 'contract') {
    return (
      <Card title="Ringkasan Nilai & Waktu Kontrak" source="Kontrak Definitif">
        <KpiRow
          items={[
            { label: 'Nilai Kontrak', value: formatRupiah(d.nilai_kontrak) },
            { label: 'Durasi Pelaksanaan', value: `${d.durasi_hari} hari` },
            { label: 'Masa Pemeliharaan', value: `${d.masa_pemeliharaan} hari` },
          ]}
        />
      </Card>
    )
  }
  return (
    <Card title="Ringkasan Dokumen RKS" source="RKS Teknis">
      <KpiRow
        items={[
          { label: 'Jumlah Bab', value: d.bab_count },
          { label: 'Risiko CSMS', value: d.resiko_csms, tone: 'text-pertamina-red' },
          { label: 'Lokasi', value: d.lokasi },
        ]}
      />
    </Card>
  )
}

export default function MatrixView({ mode, data }) {
  return mode === 'tender' ? <TenderMatrix d={data} /> : <SummaryMatrix mode={mode} d={data} />
}
