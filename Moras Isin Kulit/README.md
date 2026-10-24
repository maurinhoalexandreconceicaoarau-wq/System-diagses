# Sistem Konsultasi Penyakit Kulit

Aplikasi konsultasi berbasis Streamlit dengan akun pengguna dan admin.

## Menjalankan aplikasi

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Database SQLite berada di `database/skin_expert.db`. Admin pertama dibuat saat aplikasi dibuka pertama kali.

## Struktur data konsultasi

- `sintoma`: `kd_sintoma`, `naran`, dan `bobot` desimal antara 0.01–1.00.
- `problema`: `kd_problema`, `naran`, dan `solusi`.
- `rules`: kondisi gejala dan kesimpulan problema yang dipakai forward chaining.

Bobot awal dihitung dari kelangkaan gejala pada aturan: gejala yang lebih jarang muncul mendapat bobot lebih tinggi.

Admin dapat mengelola gejala, bobot, penyakit, solusi, dan aturan. Pengguna hanya memilih gejala lalu menerima satu hasil penyakit dengan skor kecocokan berbobot dan solusi. Skor adalah perkiraan kecocokan aturan, bukan probabilitas klinis atau diagnosis medis.

Setiap konsultasi disimpan di tabel `consultation_history` bersama pengguna, gejala pilihan, hasil, skor, dan waktu. Pengguna dapat melihat histori miliknya; admin dapat melihat histori seluruh pengguna. Dashboard masing-masing menampilkan ringkasan dan grafik konsultasi.

Tabel lama `symptoms` dan `diseases` dipertahankan sebagai kompatibilitas database. Aplikasi membaca dan mengelola data konsultasi melalui tabel sederhana `sintoma` dan `problema`.
