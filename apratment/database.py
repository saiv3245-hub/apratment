import psycopg2

def get_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="apratment_F&B",
        user="postgres",
        password="1234",
        port="5432"
    )

    return conn