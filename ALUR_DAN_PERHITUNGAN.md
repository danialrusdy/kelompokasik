# Penjelasan Alur Sistem & Perhitungan Metodologi

Dokumen ini menjelaskan bagaimana alur kerja aplikasi web K-Means Clustering ini berjalan dan detail perhitungan matematis yang digunakan di "bawah layar" (backend).

## 1. Alur Kerja Aplikasi (Workflow)

Aplikasi ini dirancang dengan tahapan sekuensial (berurutan) untuk memastikan data diproses dengan benar dari mentah hingga menjadi informasi yang berguna.

### Tahap 1: Upload Data (`/upload`)
- **Input**: Pengguna mengunggah file CSV.
- **Validasi**: Sistem mengecek apakah kolom-kolom wajib ada:
  - `CustomerID`
  - `Gender`
  - `Age`
  - `Annual Income (k$)`
  - `Spending Score (1-100)`
- **Aksi Database**: Saat file baru diupload, sistem **menghapus bersih (Truncate)** semua data lama di database untuk mencegah percampuran data. Data baru disimpan ke tabel `customers`.

### Tahap 2: Preprocessing (`/preprocessing`)
Sebelum masuk ke algoritma, data harus disiapkan agar hasil akurat.
- **Seleksi Fitur**: Algoritma hanya mengambil dua kolom fokus untuk clustering saat ini:
  1. `Annual Income`
  2. `Spending Score`
- **Normalisasi**: Data dinormalisasi menggunakan teknik **Min-Max Scalling** (penjelasan rumus di bawah).
- **Output**: Data yang sudah dinormalisasi (rentang 0-1) disimpan ke tabel `preprocessing_data`.

### Tahap 3: Proses K-Means (`/process_kmeans`)
- **Input User**: Pengguna menentukan jumlah cluster ($K$) yang diinginkan (misal: 3 cluster).
- **Proses AI**: Library `scikit-learn` menjalankan algoritma K-Means pada data yang sudah dinormalisasi.
- **Evaluasi Otomatis**: Setelah cluster terbentuk, sistem langsung menghitung kualitas cluster menggunakan **Silhouette Score** dan **Davies-Bouldin Index**.

### Tahap 4: Hasil & Visualisasi (`/results`)
Menampilkan report lengkap:
1. **Scatter Plot**: Grafik visual penyebaran data dan pembagian warna cluster.
2. **Kartu Evaluasi**: Menampilkan skor Silhouette dan DBI untuk menilai bagus/tidaknya hasil cluster.
3. **Tabel Ringkasan**: Menampilkan rata-rata (Mean) Income dan Spending Score asli (bukan yang dinormalisasi) untuk setiap cluster agar mudah dibaca manusia.

---

## 2. Detail Perhitungan (Metodologi)

Berikut adalah rumus dan logika matematika yang berjalan di backend (`app.py`).

### A. Normalisasi (Min-Max XML)
Kita menggunakan **Min-Max Scaler**. Tujuannya mengubah data ke rentang 0 sampai 1 agar variabel dengan angka besar (Income ribuan) tidak mendominasi variabel angka kecil (Score puluhan).

**Rumus:**
$$X_{new} = \frac{X - X_{min}}{X_{max} - X_{min}}$$

Dimana:
- $X$: Nilai asli data.
- $X_{min}$: Nilai terendah di kolom tersebut.
- $X_{max}$: Nilai tertinggi di kolom tersebut.

### B. Algoritma K-Means
1. **Inisialisasi**: Pilih $K$ titik pusat (centroid) secara acak (kami set `random_state=42` agar hasil konsisten/tidak berubah-ubah setiap kali run).
2. **Assignment**: Hitung jarak setiap data customer ke semua centroid (menggunakan **Euclidean Distance**). Masukkan customer ke centroid terdekat.
   $$d(p, q) = \sqrt{(p_1 - q_1)^2 + (p_2 - q_2)^2}$$
3. **Update Centroid**: Hitung ulang posisi centroid dengan mengambil rata-rata lokasi semua titik yang ada di cluster tersebut.
4. **Iterasi**: Ulangi langkah 2 & 3 sampai posisi centroid tidak berubah lagi (konvergen).

### C. Evaluasi Clustering

#### 1. Silhouette Coefficient
Mengukur seberapa mirip sebuah objek dengan clusternya sendiri dibandingkan dengan cluster lain.
- **Rentang Nilai**: -1 hingga 1.
- **Cara Baca**:
  - Mendekati **+1**: Clustering sangat bagus (terpisah jauh antar cluster).
  - Mendekati **0**: Overlapping (cluster tumpang tindih).
  - Mendekati **-1**: Salah penempatan cluster.

#### 2. Davies-Bouldin Index (DBI)
Mengukur rasio "sebaran data di dalam cluster" dibandingkan dengan "jarak antar cluster".
- **Cara Baca**: Semakin **KECIL** nilainya (mendekati 0), semakin **BAGUS**. Ini berarti clusternya padat (anggota mirip-mirip) dan terpisah jauh dari cluster lain.

---

## Kesimpulan Flow Data
`CSV Mentah` -> `DB (customers)` -> **MinMax Scaling** -> `DB (preprocessing_data)` -> **K-Means Calc** -> `DB (clustering_results)` -> **Evaluasi Metrics** -> `Visualisasi UI`
