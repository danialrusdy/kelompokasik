from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
import os
import matplotlib
matplotlib.use('Agg') # Backend for non-GUI
import matplotlib.pyplot as plt
import io
import base64
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
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

# User Model
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='admin')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Gagal. Periksa username dan password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                df = pd.read_csv(filepath)
                required_columns = ['CustomerID', 'Gender', 'Age', 'Annual Income (k$)', 'Spending Score (1-100)']
                if not all(col in df.columns for col in required_columns):
                    flash(f'Format Error. Columns must be: {", ".join(required_columns)}', 'danger')
                    return redirect(request.url)

                db.session.execute(text('DELETE FROM clustering_results'))
                db.session.execute(text('DELETE FROM preprocessing_data'))
                db.session.execute(text('DELETE FROM customers'))
                db.session.commit()

                df = df.rename(columns={
                    'Annual Income (k$)': 'AnnualIncome', 
                    'Spending Score (1-100)': 'SpendingScore'
                })
                
                df[['CustomerID', 'Gender', 'Age', 'AnnualIncome', 'SpendingScore']].to_sql(
                    'customers', con=db.engine, if_exists='append', index=False
                )
                
                flash(f'Data successfully uploaded! {len(df)} rows imported.', 'success')
                return redirect(url_for('preprocessing'))
                
            except Exception as e:
                flash(f'Error processing file: {e}', 'danger')
                print(e)
        else:
            flash('Allowed file types are CSV', 'danger')

    return render_template('upload.html')

@app.route('/preprocessing', methods=['GET', 'POST'])
@login_required
def preprocessing():
    raw_data = pd.read_sql("SELECT * FROM customers LIMIT 10", db.engine)
    
    if request.method == 'POST':
        try:
            df = pd.read_sql("SELECT CustomerID, AnnualIncome, SpendingScore FROM customers", db.engine)
            if df.empty:
                flash('No data to process.', 'warning')
                return redirect(url_for('upload'))

            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(df[['AnnualIncome', 'SpendingScore']])
            
            df_scaled = pd.DataFrame(scaled_features, columns=['AnnualIncome_Scaled', 'SpendingScore_Scaled'])
            df_scaled['CustomerID'] = df['CustomerID']
            
            db.session.execute(text('DELETE FROM preprocessing_data'))
            db.session.commit()
            
            df_scaled.to_sql('preprocessing_data', con=db.engine, if_exists='append', index=False)
            
            flash('Data successfully normalized!', 'success')
            return redirect(url_for('process_kmeans'))
            
        except Exception as e:
            flash(f'Preprocessing failed: {e}', 'danger')

    return render_template('preprocessing.html', tables=[raw_data.to_html(classes='min-w-full divide-y divide-gray-200', index=False)], titles=raw_data.columns.values)

@app.route('/process_kmeans', methods=['GET', 'POST'])
@login_required
def process_kmeans():
    if request.method == 'POST':
        try:
            k = int(request.form['k_value'])
            
            df = pd.read_sql("SELECT * FROM preprocessing_data", db.engine)
            if df.empty:
                flash('Please do preprocessing first.', 'warning')
                return redirect(url_for('preprocessing'))
            
            X = df[['AnnualIncome_Scaled', 'SpendingScore_Scaled']].values
            
            kmeans = KMeans(n_clusters=k, random_state=42)
            labels = kmeans.fit_predict(X)
            
            df_labels = pd.DataFrame({
                'CustomerID': df['CustomerID'],
                'Cluster': labels
            })
            
            db.session.execute(text('DELETE FROM clustering_results'))
            db.session.commit()
            
            df_labels.to_sql('clustering_results', con=db.engine, if_exists='append', index=False)
            
            flash(f'Clustering complete with K={k}!', 'success')
            return redirect(url_for('results'))
            
        except Exception as e:
            flash(f'Clustering failed: {e}', 'danger')
            
    return render_template('kmeans.html')

@app.route('/results')
@login_required
def results():
    try:
        # Join customers and results
        query = """
        SELECT c.*, r.Cluster 
        FROM customers c 
        JOIN clustering_results r ON c.CustomerID = r.CustomerID
        ORDER BY r.Cluster, c.CustomerID
        """
        df = pd.read_sql(query, db.engine)
        
        if df.empty:
            flash('No results found. Run clustering first.', 'warning')
            return redirect(url_for('process_kmeans'))

        # Generate Plot
        plt.figure(figsize=(10, 6))
        
        # Colors for clusters
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'cyan', 'magenta', 'yellow', 'black', 'gray']
        
        for cluster in sorted(df['Cluster'].unique()):
            cluster_data = df[df['Cluster'] == cluster]
            plt.scatter(
                cluster_data['AnnualIncome'], 
                cluster_data['SpendingScore'],
                s=50, 
                c=colors[cluster % len(colors)],
                label=f'Cluster {cluster}'
            )
            
        plt.title('Customer Segments')
        plt.xlabel('Annual Income (k$)')
        plt.ylabel('Spending Score (1-100)')
        plt.legend()
        plt.grid(True)
        
        # Save to BytesIO
        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()
        plt.close()
        
        # Cluster Summary
        summary = df.groupby('Cluster').agg({
            'CustomerID': 'count',
            'AnnualIncome': 'mean',
            'SpendingScore': 'mean'
        }).rename(columns={'CustomerID': 'Count', 'AnnualIncome': 'Avg Income', 'SpendingScore': 'Avg Score'})
        
        return render_template(
            'result.html', 
            plot_url=plot_url, 
            summary=summary.to_dict(orient='index'),
            df_head=df.head(20).to_dict(orient='records')
        )

    except Exception as e:
        flash(f'Error loading results: {e}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/recommendations')
@login_required
def recommendations():
    try:
        query = """
        SELECT c.*, r.Cluster 
        FROM customers c 
        JOIN clustering_results r ON c.CustomerID = r.CustomerID
        """
        df = pd.read_sql(query, db.engine)
        
        if df.empty:
            flash('No data for recommendations.', 'warning')
            return redirect(url_for('dashboard'))
            
        # Analysis per cluster to generate dynamic text
        cluster_stats = df.groupby('Cluster').agg({
            'AnnualIncome': 'mean',
            'SpendingScore': 'mean'
        }).reset_index()
        
        recommendations = []
        for index, row in cluster_stats.iterrows():
            cluster = int(row['Cluster'])
            income = row['AnnualIncome']
            score = row['SpendingScore']
            
            strategy = ""
            bg_class = ""
            
            if income > 70 and score > 70:
                name = "Target (High Income, High Spend)"
                strategy = "Pelanggan VIP. Tawarkan produk premium, program loyalitas eksklusif, dan layanan prioritas."
                bg_class = "bg-green-100 border-green-400 text-green-700"
            elif income > 70 and score < 40:
                name = "Hemat (High Income, Low Spend)"
                strategy = "Pelanggan potensial tapi hemat. Tawarkan promosi bundle, diskon spesial untuk produk mahal, atau branding yang menekankan value."
                bg_class = "bg-yellow-100 border-yellow-400 text-yellow-700"
            elif income < 40 and score > 70:
                name = "Boros (Low Income, High Spend)"
                strategy = "Pelanggan impulsif. Hati-hati dengan risiko kredit (jika ada). Tawarkan diskon, flash sale, dan produk trendi dengan harga terjangkau."
                bg_class = "bg-red-100 border-red-400 text-red-700"
            elif income < 40 and score < 40:
                name = "Sensitif (Low Income, Low Spend)"
                strategy = "Pelanggan sensitif harga. Tawarkan kupon diskon, produk murah meriah, dan promosi beli 1 gratis 1."
                bg_class = "bg-gray-100 border-gray-400 text-gray-700"
            else:
                name = "Standar (Middle Income, Middle Spend)"
                strategy = "Pelanggan rata-rata. Fokus pada retensi pelanggan, newsletter, dan promosi musiman standar."
                bg_class = "bg-blue-100 border-blue-400 text-blue-700"
                
            recommendations.append({
                'cluster': cluster,
                'avg_income': round(income, 2),
                'avg_score': round(score, 2),
                'name': name,
                'strategy': strategy,
                'bg_class': bg_class
            })
            
        return render_template('recommendation.html', recommendations=recommendations)

    except Exception as e:
        flash(f'Error generating recommendations: {e}', 'danger')
        return redirect(url_for('results'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
