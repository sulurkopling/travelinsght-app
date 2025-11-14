from flask import Flask, render_template, request, session, redirect, url_for
import requests
import os
from dotenv import load_dotenv
import uuid
import time

app = Flask(__name__)
load_dotenv()

app.secret_key = os.getenv("FLASK_SECRET_KEY", "rahasia_aman")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# Cache sementara di server
cached_results = {}
CACHE_TTL = 60 * 30  # 30 menit


# --------------------------------------------
# Fungsi pembersihan cache
# --------------------------------------------
def cleanup_cache():
    now = time.time()
    for k in list(cached_results.keys()):
        if now - cached_results[k]["created"] > CACHE_TTL:
            del cached_results[k]


# --------------------------------------------
# Fungsi pencarian wisata dari API SerpAPI
# --------------------------------------------
def cari_wisata_by_city(kota):
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_maps",
        "q": f"tempat wisata di {kota}",
        "type": "search",
        "api_key": SERPAPI_KEY
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("local_results", [])


# ====================================================
# 🚀 Redirect awal ke halaman beranda
# ====================================================
@app.route("/")
def root():
    return redirect(url_for("index"))


# ====================================================
# 🏠 Halaman Beranda (Landing Page)
# ====================================================
@app.route("/home")
def index():
    return render_template("home.html", active_page="home")


# ====================================================
# 🌍 Halaman pencarian wisata
# ====================================================
@app.route("/search", methods=["GET", "POST"])
def search():
    query_kota = request.args.get("kota", "").strip()

    if request.method == "POST":
        kota = request.form.get("kota", "").strip()
        if not kota:
            return render_template("index.html", pesan="Masukkan nama kota terlebih dahulu.", active_page="search")

        try:
            hasil = cari_wisata_by_city(kota)
        except Exception as e:
            return render_template("index.html", pesan=f"Gagal mengambil data API: {e}", active_page="search")

        if not hasil:
            return render_template("index.html", pesan=f"Tidak ditemukan hasil untuk kota '{kota}'.", active_page="search")

        tempat_wisata = []
        for i, item in enumerate(hasil):
            tempat_wisata.append({
                "id": i,
                "name": item.get("title", "Nama tidak tersedia"),
                "address": item.get("address", "Alamat tidak tersedia"),
                "rating": float(item.get("rating")) if item.get("rating") else 0.0,
                "thumbnail": item.get("thumbnail", "https://via.placeholder.com/400x300?text=No+Image"),
                "description": item.get("snippet") or item.get("type") or "Deskripsi tidak tersedia",
                "maps_link": item.get("link", f"https://www.google.com/maps/search/?api=1&query={item.get('title','')}"),
            })

        cleanup_cache()
        cache_id = str(uuid.uuid4())
        cached_results[cache_id] = {"created": time.time(), "kota": kota, "results": tempat_wisata}
        session["cache_id"] = cache_id
        session["last_kota"] = kota

        # Ambil 10 wisata teratas berdasarkan rating
        top10 = sorted(tempat_wisata, key=lambda x: x["rating"], reverse=True)[:10]
        chart_labels = [t["name"] for t in top10]
        chart_values = [t["rating"] for t in top10]

        return render_template(
            "index.html",
            tempat_wisata=tempat_wisata,
            kota=kota,
            chart_labels=chart_labels,
            chart_values=chart_values,
            active_page="search"
        )

    # Ambil dari cache
    cache_id = session.get("cache_id")
    if query_kota:
        for cid, data in cached_results.items():
            if data["kota"].lower() == query_kota.lower():
                cache_id = cid
                break

    if cache_id and cache_id in cached_results:
        data = cached_results[cache_id]
        tempat_wisata = data["results"]
        kota = data["kota"]

        top10 = sorted(tempat_wisata, key=lambda x: x["rating"], reverse=True)[:10]
        chart_labels = [t["name"] for t in top10]
        chart_values = [t["rating"] for t in top10]

        return render_template(
            "index.html",
            tempat_wisata=tempat_wisata,
            kota=kota,
            chart_labels=chart_labels,
            chart_values=chart_values,
            active_page="search"
        )

    return render_template("index.html", active_page="search")


# ====================================================
# 🏞️ Halaman Detail Wisata
# ====================================================
@app.route("/detail/<int:id>")
def detail(id):
    kota = request.args.get("kota") or session.get("last_kota")
    cache_id = session.get("cache_id")

    tempat = None
    if cache_id and cache_id in cached_results:
        data = cached_results[cache_id]
        if 0 <= id < len(data["results"]):
            tempat = data["results"][id]
            kota = data["kota"]

    if not tempat:
        return render_template("detail.html", pesan="Data tidak ditemukan.", active_page="search")

    return render_template("detail.html", tempat=tempat, kota=kota, active_page="search")


# ====================================================
# ℹ️ Halaman Tentang
# ====================================================
@app.route("/about")
def about():
    return render_template("about.html", active_page="about")


# ====================================================
# Jalankan server Flask
# ====================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
