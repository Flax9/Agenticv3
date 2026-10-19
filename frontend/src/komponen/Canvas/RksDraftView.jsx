// Pratinjau draf RKS hasil agent (skema JSON `_RKS_JSON_SCHEMA` milik tim AI).
// Skema konten tabel belum baku, jadi beberapa bentuk umum ditangani dan sisanya ditampilkan apa adanya.

function asText(value) {
  if (value === null || value === undefined) return ''
  return typeof value === 'string' ? value : JSON.stringify(value)
}

function TableContent({ konten }) {
  let headers = []
  let rows = []
  if (Array.isArray(konten)) {
    if (konten.length && !Array.isArray(konten[0]) && typeof konten[0] === 'object') {
      headers = Object.keys(konten[0])
      rows = konten.map((r) => headers.map((h) => r[h]))
    } else {
      rows = konten
    }
  } else if (konten && typeof konten === 'object') {
    headers = konten.headers ?? konten.header ?? konten.kolom ?? []
    rows = konten.rows ?? konten.baris ?? konten.data ?? []
  }
  if (!rows.length) return <pre className="whitespace-pre-wrap text-xs">{asText(konten)}</pre>

  return (
    <div className="overflow-x-auto">
      <table className="doc-table">
        {headers.length > 0 && (
          <thead>
            <tr>
              {headers.map((h) => (
                <th key={asText(h)}>{asText(h)}</th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {(Array.isArray(row) ? row : [row]).map((cell, j) => (
                <td key={j}>{asText(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function SubBabContent({ tipe, konten }) {
  if (tipe === 'heading_only' || konten === undefined || konten === null || konten === '') return null
  if (tipe === 'table') return <TableContent konten={konten} />
  if (tipe === 'numbered_list' || tipe === 'bullet_list') {
    const items = Array.isArray(konten) ? konten : asText(konten).split('\n').filter(Boolean)
    const List = tipe === 'numbered_list' ? 'ol' : 'ul'
    return (
      <List className={`${tipe === 'numbered_list' ? 'list-decimal' : 'list-disc'} space-y-1 pl-6`}>
        {items.map((item, i) => (
          <li key={i}>{asText(item)}</li>
        ))}
      </List>
    )
  }
  return <p className="whitespace-pre-wrap text-justify">{asText(konten)}</p>
}

const PENGESAHAN = [
  ['disusun_oleh', 'Disusun oleh'],
  ['diperiksa_oleh', 'Diperiksa oleh'],
  ['disetujui_oleh', 'Disetujui oleh'],
]

export default function RksDraftView({ draft }) {
  const d = draft.konten_json ?? {}
  const cover = d.cover_page ?? {}
  const meta = d.metadata ?? {}
  const pengesahan = d.pengesahan ?? {}
  const bab = Array.isArray(d.bab) ? d.bab : []

  return (
    <article className="relative mb-8 min-h-[900px] rounded border border-pertamina-gray-300 bg-white px-6 py-8 shadow-sheet sm:px-14 sm:py-12">
      <header className="mb-7 flex items-start justify-between gap-4 border-b-2 border-pertamina-navy pb-4">
        <div>
          <div className="text-[15px] font-extrabold uppercase tracking-wide text-pertamina-navy">
            {cover.nama_perusahaan || 'PT PERTAMINA'}
          </div>
          <div className="mt-0.5 text-[11px] font-semibold text-pertamina-gray-500">
            Rencana Kerja &amp; Syarat-Syarat · Risiko CSMS {cover.resiko_csms || '—'}
          </div>
        </div>
        <div className="shrink-0 rounded-md border-[1.5px] border-amber-500 px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-widest text-amber-600">
          Draf {draft.versi}
        </div>
      </header>

      <div className="mb-9 mt-6 text-center">
        <div className="mb-1.5 text-lg font-extrabold uppercase text-pertamina-navy">Rencana Kerja dan Syarat-Syarat</div>
        <div className="mx-auto max-w-[620px] text-sm font-bold uppercase leading-snug text-pertamina-gray-900">
          {cover.judul_pekerjaan || draft.judul_dokumen}
        </div>
        <div className="mt-2.5 inline-block rounded-md bg-pertamina-gray-100 px-3 py-1 font-mono text-xs font-semibold text-pertamina-gray-700">
          Nomor: {meta.nomor_dokumen || '—'} · Tahun {meta.tahun || '—'}
        </div>
      </div>

      {Object.keys(pengesahan).length > 0 && (
        <>
          <div className="doc-section-title">Lembar Pengesahan</div>
          <table className="doc-table mb-6">
            <tbody>
              {PENGESAHAN.map(([key, label]) => (
                <tr key={key}>
                  <td className="w-40 font-semibold">{label}</td>
                  <td>{pengesahan[key]?.nama || '—'}</td>
                  <td>{pengesahan[key]?.jabatan || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {bab.length === 0 && <p className="text-xs text-pertamina-gray-500">Draf belum memiliki bab.</p>}
      {bab.map((b) => (
        <section key={`${b.nomor}-${b.judul}`} className="mb-6">
          <div className="doc-section-title">
            BAB {b.nomor} — {b.judul}
          </div>
          <div className="space-y-3 text-[13px] leading-relaxed text-pertamina-gray-900">
            {(b.sub_bab ?? []).map((s) => (
              <div key={`${s.nomor}-${s.judul}`}>
                <div className="mb-1 font-bold text-pertamina-navy">
                  {s.nomor} {s.judul}
                </div>
                <SubBabContent tipe={s.tipe} konten={s.konten} />
              </div>
            ))}
          </div>
        </section>
      ))}
    </article>
  )
}
