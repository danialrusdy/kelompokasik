from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

# === PERUBAHAN UTAMA ===
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sqlalchemy import text

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sangatrahasia123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://kelompokasik:passnyasusahbanget@154.26.135.171:3306/kelompokasik'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ================= USER MODEL =================
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='admin')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ================= ROUTES =================
@app.route('/')
def index():
    return redirect(url_for('login'))

# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Login gagal.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ---------- DASHBOARD ----------
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# ---------- UPLOAD DATA ----------
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename.endswith('.csv'):
            flash('File harus CSV', 'danger')
            return redirect(request.url)

        path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(path)

        df = pd.read_csv(path)

        required = ['CustomerID', 'Gender', 'Age', 'Annual Income (k$)', 'Spending Score (1-100)']
        if not all(col in df.columns for col in required):
            flash('Format kolom tidak sesuai', 'danger')
            return redirect(request.url)

        # Reset data
        db.session.execute(text('DELETE FROM customers'))
        db.session.execute(text('DELETE FROM preprocessing_data'))
        db.session.execute(text('DELETE FROM clustering_results'))
        db.session.commit()

        df = df.rename(columns={
            'Annual Income (k$)': 'AnnualIncome',
            'Spending Score (1-100)': 'SpendingScore'
        })

        df.to_sql('customers', db.engine, if_exists='append', index=False)
        flash('Dataset berhasil diupload', 'success')
        return redirect(url_for('preprocessing'))

    return render_template('upload.html')

# ---------- PREPROCESSING ----------
@app.route('/preprocessing', methods=['GET', 'POST'])
@login_required
def preprocessing():
    raw = pd.read_sql("SELECT * FROM customers LIMIT 10", db.engine)

    if request.method == 'POST':
        df = pd.read_sql(
            "SELECT CustomerID, AnnualIncome, SpendingScore FROM customers",
            db.engine
        )

        # === MIN-MAX NORMALIZATION (SESUAI EXCEL) ===
        scaler = MinMaxScaler()
        scaled = scaler.fit_transform(df[['AnnualIncome', 'SpendingScore']])

        df_scaled = pd.DataFrame(
            scaled,
            columns=['AnnualIncome_Scaled', 'SpendingScore_Scaled']
        )
        df_scaled['CustomerID'] = df['CustomerID']

        db.session.execute(text('DELETE FROM preprocessing_data'))
        db.session.commit()
        df_scaled.to_sql('preprocessing_data', db.engine, if_exists='append', index=False)

        norm = pd.read_sql("SELECT * FROM preprocessing_data LIMIT 10", db.engine)

        return render_template(
            'preprocessing.html',
            tables=[raw.to_html(index=False)],
            normalized_table=[norm.to_html(index=False)],
            show_next_step=True
        )

    return render_template(
        'preprocessing.html',
        tables=[raw.to_html(index=False)]
    )

# ---------- K-MEANS ----------
@app.route('/process_kmeans', methods=['GET', 'POST'])
@login_required
def process_kmeans():
    if request.method == 'POST':
        k = int(request.form['k_value'])

        df = pd.read_sql("SELECT * FROM preprocessing_data", db.engine)
        X = df[['AnnualIncome_Scaled', 'SpendingScore_Scaled']].values

        # === K-MEANS FIXED RANDOM STATE ===
        kmeans = KMeans(n_clusters=k, random_state=42)
        labels = kmeans.fit_predict(X)

        result = pd.DataFrame({
            'CustomerID': df['CustomerID'],
            'Cluster': labels
        })

        db.session.execute(text('DELETE FROM clustering_results'))
        db.session.commit()
        result.to_sql('clustering_results', db.engine, if_exists='append', index=False)

        silhouette_avg = silhouette_score(X, labels)
        dbi_score = davies_bouldin_score(X, labels)

        flash('Clustering berhasil', 'success')
        return redirect(url_for('results', silhouette=round(silhouette_avg, 3), dbi=round(dbi_score, 3)))

    return render_template('kmeans.html')

# ---------- RESULTS ----------
@app.route('/results')
@login_required
def results():
    query = """
    SELECT c.*, r.Cluster
    FROM customers c
    JOIN clustering_results r ON c.CustomerID = r.CustomerID
    """
    df = pd.read_sql(query, db.engine)

    # Plot
    plt.figure(figsize=(8, 5))
    for c in sorted(df.Cluster.unique()):
        d = df[df.Cluster == c]
        plt.scatter(d.AnnualIncome, d.SpendingScore, label=f'Cluster {c}')
    plt.legend()
    plt.xlabel('Annual Income')
    plt.ylabel('Spending Score')
    plt.grid()

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.read()).decode()
    plt.close()

    summary = df.groupby('Cluster').agg(
        Count=('CustomerID', 'count'),
        AvgIncome=('AnnualIncome', 'mean'),
        AvgScore=('SpendingScore', 'mean')
    )

    return render_template(
        'result.html',
        plot_url=plot_url,
        summary=summary.to_dict('index'),
        df_head=df.head(20).to_dict('records'),
        silhouette=request.args.get('silhouette'),
        dbi=request.args.get('dbi')
    )

# ---------- RECOMMENDATION ----------
@app.route('/recommendations')
@login_required
def recommendations():
    query = """
    SELECT c.*, r.Cluster
    FROM customers c
    JOIN clustering_results r ON c.CustomerID = r.CustomerID
    """
    df = pd.read_sql(query, db.engine)

    stats = df.groupby('Cluster').agg(
        avg_income=('AnnualIncome', 'mean'),
        avg_score=('SpendingScore', 'mean')
    ).reset_index()

    recs = []
    for _, r in stats.iterrows():
        recs.append({
            'cluster': int(r.Cluster),
            'avg_income': round(r.avg_income, 2),
            'avg_score': round(r.avg_score, 2),
            'name': 'Segment Pelanggan',
            'strategy': 'Strategi pemasaran disesuaikan dengan karakteristik cluster',
            'bg_class': 'bg-blue-100 border-blue-400 text-blue-700'
        })

    return render_template('recommendation.html', recommendations=recs)

if __name__ == '__main__':
    app.run(debug=True)