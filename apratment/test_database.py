from database import get_connection

conn = None
cursor = None

try:
    conn = get_connection()

    print("1. เชื่อมต่อ PostgreSQL สำเร็จ")

    cursor = conn.cursor()

    cursor.execute("SELECT current_database(), current_user;")
    result = cursor.fetchone()

    print("2. Database:", result[0])
    print("3. User:", result[1])

    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'user'
        );
        """
    )

    table_exists = cursor.fetchone()[0]

    print("4. พบตาราง user:", table_exists)

    cursor.execute(
        '''
        SELECT
            user_id,
            user_name,
            role,
            is_active
        FROM public."user"
        '''
    )

    users = cursor.fetchall()

    print("5. ข้อมูลผู้ใช้:")

    for user in users:
        print(user)

except Exception as e:

    print("")
    print("เกิดข้อผิดพลาด")
    print("ประเภท:", type(e).__name__)
    print("รายละเอียด:", e)

finally:

    if cursor:
        cursor.close()

    if conn:
        conn.close()