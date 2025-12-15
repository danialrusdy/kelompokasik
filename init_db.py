import pymysql
from werkzeug.security import generate_password_hash

# Database Configuration
db_config = {
    'host': '154.26.135.171',
    'port': 3306,
    'user': 'kelompokasik',
    'password': 'passnyasusahbanget',
    'database': 'kelompokasik'
}

def init_db():
    try:
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()
        
        print("Connected to database.")

        # Read schema
        with open('database.sql', 'r') as f:
            schema = f.read()

        # Execute schema commands (split by ;)
        commands = schema.split(';')
        for command in commands:
            if command.strip():
                cursor.execute(command)
        
        print("Tables initialized.")

        # Check if admin exists
        cursor.execute("SELECT * FROM users WHERE username = 'kelompokasik'")
        admin = cursor.fetchone()

        if not admin:
            hashed_password = generate_password_hash('sandinyasusah', method='pbkdf2:sha256')
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                ('kelompokasik', hashed_password, 'admin')
            )
            connection.commit()
            print("Admin user created successfully.")
        else:
            print("Admin user already exists.")

        cursor.close()
        connection.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    init_db()
