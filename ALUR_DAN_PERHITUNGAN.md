# Penjelasan Alur Sistem & Perhitungan Metodologi

Dokumen ini menjelaskan bagaimana alur kerja aplikasi web K-Means Clustering ini berjalan, detail perhitungan matematis, **dan implementasi kodenya** di `app.py`.

## 1. Alur Kerja Aplikasi (Workflow)

Aplikasi ini dirancang dengan tahapan sekuensial (berurutan) untuk memastikan data diproses dengan benar dari mentah hingga menjadi informasi yang berguna.

### Tahap 1: Upload Data (`/upload`)
- **Input**: Pengguna mengunggah file CSV.
- **Validasi**: Sistem mengecek kolom wajib.
- **Kode Implementasi**:
```python
# app.py baris 88-106
df = pd.read_csv(path)
required = ['CustomerID', 'Gender', 'Age', 'Annual Income (k$)', 'Spending Score (1-100)']
# ... validasi ...
df.to_sql('customers', db.engine, if_exists='append', index=False)
```

### Tahap 2: Preprocessing (`/preprocessing`)
Sebelum masuk ke algoritma, data harus disiapkan agar hasil akurat.

#### Normalisasi (Min-Max Scaling)
Kita menggunakan **Min-Max Scaler**. Tujuannya mengubah data ke rentang 0 sampai 1.

**Rumus Matematika:**
$$X_{new} = \frac{X - X_{min}}{X_{max} - X_{min}}$$

**Implementasi Kode (`app.py`):**
```python
# Import library
from sklearn.preprocessing import MinMaxScaler

# Ambil data yang akan dinormalisasi
df = pd.read_sql("SELECT CustomerID, AnnualIncome, SpendingScore FROM customers", db.engine)

# Inisialisasi Scaler
scaler = MinMaxScaler()

# Proses hitung Min-Max (Fit & Transform sekaligus)
scaled = scaler.fit_transform(df[['AnnualIncome', 'SpendingScore']])

# Simpan hasil ke DataFrame baru
df_scaled = pd.DataFrame(scaled, columns=['AnnualIncome_Scaled', 'SpendingScore_Scaled'])
```

### Tahap 3: Proses K-Means (`/process_kmeans`)
Proses utama pengelompokan data.

#### Algoritma K-Means
1. **Inisialisasi**: Pilih $K$ titik pusat (centroid).
2. **Assignment**: Hitung jarak (Euclidean Distance).
3. **Update**: Cari posisi centroid baru.

**Implementasi Kode (`app.py`):**
```python
# Import library
from sklearn.cluster import KMeans

# Ambil data hasil normalisasi dari database
df = pd.read_sql("SELECT * FROM preprocessing_data", db.engine)
X = df[['AnnualIncome_Scaled', 'SpendingScore_Scaled']].values

# Jalankan K-Means
# n_clusters=k : Jumlah cluster pilihan user
# random_state=42 : Agar hasil konsisten (tidak berubah-ubah)
kmeans = KMeans(n_clusters=k, random_state=42)

# Lakukan training dan prediksi label sekaligus
labels = kmeans.fit_predict(X)
```

### Tahap 4: Evaluasi & Hasil (`/results`)
Setelah cluster terbentuk, kita hitung kualitasnya.

#### 1. Silhouette Coefficient & DBI
- **Silhouette**: Mengukur kemiripan dengan cluster sendiri vs cluster lain. (Mendekati 1 = Bagus).
- **DBI (Davies-Bouldin)**: Mengukur rasio sebaran data. (Mendekati 0 = Bagus).

**Implementasi Kode (`app.py`):**
```python
# Import metrics
from sklearn.metrics import silhouette_score, davies_bouldin_score

# --- Dihitung SETELAH proses clustering ---

# Hitung Silhouette Score
# Parameter: Data (X) dan Label hasil cluster (labels)
silhouette_avg = silhouette_score(X, labels)

# Hitung Davies-Bouldin Index
dbi_score = davies_bouldin_score(X, labels)

# Kirim hasil ke halaman results
return redirect(url_for('results', silhouette=round(silhouette_avg, 3), dbi=round(dbi_score, 3)))
```

---

## Kesimpulan Flow Data & Kode
1. **Upload**: `pd.read_csv` -> Simpan ke DB.
2. **Preprocessing**: `MinMaxScaler().fit_transform()` -> Ubah skala 0-1.
3. **Clustering**: `KMeans(n_clusters=k).fit_predict()` -> Kelompokkan data.
4. **Evaluasi**: `silhouette_score()` & `davies_bouldin_score()` -> Nilai kualitas.
