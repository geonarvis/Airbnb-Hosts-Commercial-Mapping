import psycopg2
from psycopg2.extras import RealDictCursor

def create_indexes():
    # 使用与主应用相同的数据库配置
    DB_CONFIG = {
        'host': 'localhost',
        'database': 'listings_airbnb',
        'user': 'postgres',
        'password': '7330',
        'port': '5432'
    }

    # 索引定义
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_listings_city ON listings(city)",
        "CREATE INDEX IF NOT EXISTS idx_listings_first_review ON listings(first_review)",
        "CREATE INDEX IF NOT EXISTS idx_listings_geom ON listings USING GIST(geom)",
        "CREATE INDEX IF NOT EXISTS idx_listings_host_id ON listings(host_id)",
        "CREATE INDEX IF NOT EXISTS idx_listings_city_first_review ON listings(city, first_review)"
    ]

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                for index in indexes:
                    print(f"Creating index: {index}")
                    cur.execute(index)
                    conn.commit()
                print("All indexes created successfully")
    except Exception as e:
        print(f"Error creating indexes: {str(e)}")

if __name__ == "__main__":
    create_indexes()