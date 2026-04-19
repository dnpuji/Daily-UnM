import streamlit as st
import pandas as pd
import requests
import datetime
import uuid
import plotly.express as px

# --- 1. KONFIGURASI DATABASE (WAJIB DIISI) ---
BIN_ID = "69e4b8be36566621a8cc448e"
API_KEY = "$2a$10$.U90wS4DZy12Vrmq4uBeF.uBIOac15LPqpzJZyPp7NTfQvxhoEo3W"
PIPEDREAM_URL = "https://eo5jyzaisu8ezte.m.pipedream.net"

URL_JSONBIN = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
HEADERS = {"X-Master-Key": API_KEY, "Content-Type": "application/json"}

# --- 2. KONFIGURASI HALAMAN & CSS ---
st.set_page_config(page_title="GPA Monitoring v6.2", page_icon="🌱", layout="centered")

st.markdown("""
    <style>
    .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
    div[data-testid="stExpander"] { border: 1px solid #e0e0e0; border-radius: 10px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNGSI PENDUKUNG (FORMAT ANGKA & CLOUD) ---
def fmt_num(val):
    if val is None or val == "": return "0"
    try:
        f = float(val)
        return f"{int(f)}" if f.is_integer() else f"{f}"
    except: return str(val)

def load_data_from_cloud():
    try:
        response = requests.get(f"{URL_JSONBIN}/latest", headers=HEADERS)
        if response.status_code == 200:
            return response.json()["record"]
    except: return []
    return []

def save_data_to_cloud(new_history):
    try:
        # Simpan 100 data terakhir agar loading tetap ringan
        requests.put(URL_JSONBIN, json=new_history[:100], headers=HEADERS)
    except Exception as e:
        st.error(f"Gagal Sinkronisasi Cloud: {e}")

# --- 4. INISIALISASI SESSION STATE ---
if 'history' not in st.session_state:
    with st.spinner("Memanggil Data Cloud..."):
        st.session_state.history = load_data_from_cloud()

if 'master_pengawas' not in st.session_state: st.session_state.master_pengawas = ["Pak Puji", "Pak Hamim", "Pak Rexa", "Pak Safi'i", "Thony"]
if 'master_kegiatan' not in st.session_state: st.session_state.master_kegiatan = ["Aplikasi NPK", "Aplikasi ZA", "Spot Spraying", "Manual Upkeep"]
if 'master_bahan' not in st.session_state: st.session_state.master_bahan = ["NPK", "ZA", "Roundup", "Gramoxone", "Garlon"]
if 'paddocks' not in st.session_state: st.session_state.paddocks = [{"name": "", "luas": None}]
if 'bahans' not in st.session_state: st.session_state.bahans = [{"name": "", "dosis": None, "satuan": "Kg"}]

def reset_form():
    for key in list(st.session_state.keys()):
        if any(key.startswith(p) for p in ["in_", "p_n_", "p_l_", "b_n_", "b_d_", "b_s_"]):
            del st.session_state[key]
    st.session_state.paddocks = [{"name": "", "luas": None}]
    st.session_state.bahans = [{"name": "", "dosis": None, "satuan": "Kg"}]

st.title("🌱 GPA Monitoring v6.2 (Sync)")
tab_in, tab_wa, tab_dash, tab_hist, tab_mas = st.tabs(["📝 INPUT", "📱 REKAP", "📊 DASH", "📜 HIST", "⚙️ MASTER"])
# ==========================================
# TAB 1: FORM INPUT
# ==========================================
with tab_in:
    tgl = st.date_input("Tanggal", datetime.date.today(), key="in_tgl")
    pengawas = st.selectbox("Nama Pengawas", st.session_state.master_pengawas, key="in_user")
    
    c1, c2 = st.columns(2)
    kegiatan = c1.selectbox("Kegiatan", st.session_state.master_kegiatan, key="in_keg")
    tipe = c2.selectbox("Tipe Laporan", ["Planning", "Hasil"], key="in_tipe")
    hk = st.number_input("Total HK", min_value=0.0, step=0.5, value=None, key="in_hk", placeholder="Ketik jumlah HK")

    st.markdown("---")
    st.subheader("📍 Lokasi Paddock")
    total_luas = 0.0
    for i, p in enumerate(st.session_state.paddocks):
        cols = st.columns([2, 1])
        st.session_state.paddocks[i]["name"] = cols[0].text_input(f"Paddock {i+1}", value=p["name"], key=f"p_n_{i}", placeholder="Nama")
        st.session_state.paddocks[i]["luas"] = cols[1].number_input(f"Ha {i+1}", value=p["luas"], key=f"p_l_{i}", placeholder="0")
        total_luas += (st.session_state.paddocks[i]["luas"] or 0.0)
    
    if st.button("➕ Tambah Paddock"): st.session_state.paddocks.append({"name": "", "luas": None}); st.rerun()

    st.markdown("---")
    st.subheader("🧪 Penggunaan Bahan")
    for i, b in enumerate(st.session_state.bahans):
        b_n = st.selectbox(f"Bahan {i+1}", [""] + st.session_state.master_bahan, key=f"b_n_{i}")
        c3, c4, c5 = st.columns([2, 2, 2])
        b_d = c3.number_input(f"Dosis {i+1}", value=b["dosis"], key=f"b_d_{i}", placeholder="0")
        b_s = c4.selectbox(f"Sat {i+1}", ["Kg", "L", "mL", "Gram", "Pcs"], key=f"b_s_{i}")
        t_kebutuhan = round(total_luas * (b_d or 0.0), 2)
        c5.text_input(f"Total {i+1}", value=f"{fmt_num(t_kebutuhan)} {b_s}", disabled=True)
        st.session_state.bahans[i] = {"name": b_n, "dosis": b_d, "satuan": b_s}

    if st.button("➕ Tambah Bahan"): st.session_state.bahans.append({"name": "", "dosis": None, "satuan": "Kg"}); st.rerun()

    st.markdown("---")
    unit_nm = st.text_input("Nama Alat/Unit", key="in_unit")
    cx, cy, cz = st.columns(3)
    val_rdy = cx.number_input("🟢 Rdy", value=None, key="in_rdy", placeholder="0")
    val_bdn = cy.number_input("🔴 Bdn", value=None, key="in_bdn", placeholder="0")
    val_sby = cz.number_input("🟡 Sby", value=None, key="in_sby", placeholder="0")
    ket_add = st.text_area("Keterangan Tambahan", key="in_ket")

    if st.button("💾 SIMPAN & KIRIM DATA", type="primary"):
        if not kegiatan or not st.session_state.paddocks[0]["name"]:
            st.error("Mohon isi minimal Kegiatan dan 1 Paddock!")
        else:
            payload = {
                "id": str(uuid.uuid4())[:8], "pengirim": pengawas, "tgl": str(tgl), "type": tipe, 
                "kegiatan": kegiatan, "hk": hk or 0, "unit": unit_nm or "-", 
                "rdy": val_rdy or 0, "bdn": val_bdn or 0, "sby": val_sby or 0, "ket": ket_add or "-",
                "data_paddock": [p for p in st.session_state.paddocks if p["name"]],
                "data_bahan": [b for b in st.session_state.bahans if b["name"]]
            }
            with st.spinner("Mengamankan Data ke Cloud..."):
                try: requests.post(PIPEDREAM_URL, json=payload)
                except: pass
                st.session_state.history.insert(0, payload)
                save_data_to_cloud(st.session_state.history)
                reset_form()
                st.success("✅ Data Berhasil Disimpan & Sinkron!"); st.rerun()
# ==========================================
# TAB 2: REKAP WA
# ==========================================
with tab_wa:
    st.subheader("📱 Susun Rekap WA")
    tgl_wa = st.date_input("Pilih Tanggal", datetime.date.today(), key="wa_tgl")
    logs = [d for d in st.session_state.history if d['tgl'] == str(tgl_wa)]
    
    if logs:
        opts = {f"{d['id']} - {d['kegiatan']} ({d['type']})": d for d in logs}
        sel_keys = st.multiselect("Pilih & Urutkan laporan:", options=list(opts.keys()), default=list(opts.keys()))
        
        selected_types = set([opts[k]['type'] for k in sel_keys])
        if "Planning" in selected_types and "Hasil" not in selected_types: judul = "DAILY PLANNING"
        elif "Hasil" in selected_types and "Planning" not in selected_types: judul = "DAILY HASIL"
        else: judul = "DAILY PLANNING & HASIL"

        tgl_indo = datetime.datetime.strptime(str(tgl_wa), "%Y-%m-%d").strftime("%d/%m/%Y")
        rekap = f"*{judul}*\n📅 *Tanggal:* {tgl_indo}\n"
        
        for key in sel_keys:
            d = opts[key]
            rekap += f"\n*-------------------------*\n👤 *Pengawas:* {d['pengirim']}\n📝 *{d['kegiatan']}*\n" 
            rekap += f"👷 HK: {fmt_num(d['hk'])} | 🚜 Unit: {d['unit']} (R:{fmt_num(d['rdy'])} B:{fmt_num(d['bdn'])} S:{fmt_num(d['sby'])})\n"
            rekap += f"📍 *Paddock:* " + ", ".join([f"{p['name']} ({fmt_num(p['luas'])}Ha)" for p in d['data_paddock']]) + "\n"
            if d['data_bahan']:
                rekap += f"🧪 *Bahan:* " + ", ".join([f"{b['name']} ({fmt_num(b['dosis'])} {b['satuan']}/Ha)" for b in d['data_bahan']]) + "\n"
            rekap += f"ℹ️ *Ket:* {d['ket']}\n"
        st.code(rekap, language="text")
        
        st.markdown("#### 🛠️ Edit Item Hari Ini")
        for i, d in enumerate(logs):
            with st.expander(f"Edit: {d['kegiatan']} - {d['id']}"):
                col_e1, col_e2 = st.columns(2)
                e_p = col_e1.selectbox("Pengawas", st.session_state.master_pengawas, index=st.session_state.master_pengawas.index(d['pengirim']) if d['pengirim'] in st.session_state.master_pengawas else 0, key=f"ep_{i}")
                e_h = col_e2.number_input("HK", value=float(d['hk']), key=f"eh_{i}")
                if st.button("Simpan Perubahan", key=f"bs_{i}"):
                    d['pengirim'] = e_p; d['hk'] = e_h
                    save_data_to_cloud(st.session_state.history)
                    st.success("Tersimpan!"); st.rerun()
                if st.button("🗑️ Hapus", key=f"bd_{i}"):
                    st.session_state.history = [x for x in st.session_state.history if x['id'] != d['id']]
                    save_data_to_cloud(st.session_state.history)
                    st.rerun()
    else: st.info("Tidak ada data.")
# ==========================================
# TAB 3, 4, 5: DASHBOARD, HIST, MASTER
# ==========================================
with tab_dash:
    st.subheader("📊 Monitoring HK & Luas")
    if len(st.session_state.history) > 1:
        df = pd.DataFrame([{"Tgl": x['tgl'], "Tipe": x['type'], "HK": float(x['hk'] or 0)} for x in st.session_state.history if x['id'] != "Awal"])
        st.plotly_chart(px.bar(df, x="Tgl", y="HK", color="Tipe", barmode="group"), use_container_width=True)
    else: st.info("Data Dashboard akan muncul setelah input pertama.")

with tab_hist:
    st.subheader("📜 Riwayat Laporan Terpusat")
    for h in st.session_state.history:
        if h['id'] == "Awal": continue
        with st.expander(f"{h['tgl']} - {h['kegiatan']} ({h['pengirim']})"):
            st.json(h)

with tab_mas:
    st.subheader("⚙️ Master Data Tim")
    for key, label in [('master_pengawas', 'Pengawas'), ('master_kegiatan', 'Kegiatan'), ('master_bahan', 'Bahan')]:
        new = st.text_input(f"Tambah {label}", key=f"new_{key}")
        if st.button(f"Simpan {label}", key=f"btn_{key}"):
            if new: st.session_state[key].append(new); st.rerun()
        st.write(f"Daftar saat ini: {', '.join(st.session_state[key])}")
