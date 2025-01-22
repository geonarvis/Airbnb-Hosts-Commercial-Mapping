from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import h3
from typing import List, Dict
from collections import Counter
import json
from functools import lru_cache
import geopandas as gpd
from fastapi.responses import JSONResponse
from utils.logger import logger
from databases import Database
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI()

# CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://www.geonarvis.com",
        "http://www.geonarvis.com",
        "https://geonarvis.com",
        "http://geonarvis.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# database config
DB_CONFIG = {
    'host': 'localhost',
    'database': 'listings_airbnb',
    'user': 'postgres',
    'password': '7330', 
    'port': '5432'
}

DATABASE_URL = "postgresql://postgres:7330@localhost:5432/listings_airbnb"
database = Database(DATABASE_URL)

# 添加一个简单的内存缓存
city_cache = {}

@app.on_event("startup")
async def startup():
    await database.connect()
    
    # 从数据库获取所有城市
    query = "SELECT DISTINCT city FROM listings WHERE geom IS NOT NULL AND first_review IS NOT NULL"
    cities = await database.fetch_all(query=query)
    
    # 预热所有有效城市的数据
    for record in cities:
        city = record['city']
        try:
            # 预加载城市数据到缓存
            await get_city_listings(city)
            logger.info(f"Successfully preloaded data for {city}")
        except Exception as e:
            logger.error(f"Failed to preload data for {city}: {e}")

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

def get_spatial_data(
    cur,
    city_name: str,
    host_ids: list = None,
    view_type: str = 'grid'
) -> dict:
    """统一处理空间数据查询"""
    query = """
        SELECT 
            host_id,
            ST_Y(geom) as latitude,
            ST_X(geom) as longitude,
            {extra_fields}
            ST_Envelope(ST_Collect(geom)) as bounds
        FROM listings
        WHERE city = %s
        {host_filter}
        AND geom IS NOT NULL
    """
    
    extra_fields = "name, price," if view_type == 'scatter' else ""
    host_filter = "AND host_id = ANY(%s)" if host_ids else ""
    
    params = [city_name]
    if host_ids:
        params.append(host_ids)
        
    cur.execute(query.format(
        extra_fields=extra_fields,
        host_filter=host_filter
    ), params)
    
    return cur.fetchall()

def calculate_hex_grid(coordinates: list, resolution: int = 9) -> dict:
    """统一处理六边形网格计算"""
    hex_counts = Counter(
        h3.geo_to_h3(lat, lng, resolution)
        for lat, lng in coordinates
    )
    
    return {
        'hexagons': [
            {
                'id': str(hex_id),
                'boundary': [list(p) for p in h3.h3_to_geo_boundary(hex_id)],
                'center': list(h3.h3_to_geo(hex_id)),
                'points_count': count
            }
            for hex_id, count in hex_counts.items()
        ],
        'total_hexagons': len(hex_counts),
        'total_points': sum(hex_counts.values())
    }

@lru_cache(maxsize=128)
def get_city_bounds(cur, city_name: str) -> dict:
    """缓存城市边界数据"""
    cur.execute("""
        SELECT 
            ST_YMin(ST_Collect(geom)) as min_lat,
            ST_YMax(ST_Collect(geom)) as max_lat,
            ST_XMin(ST_Collect(geom)) as min_lng,
            ST_XMax(ST_Collect(geom)) as max_lng
        FROM listings
        WHERE city = %s
        AND geom IS NOT NULL
    """, (city_name,))
    return cur.fetchone()

def process_coordinates_batch(coordinates: list, batch_size: int = 1000):
    """批量处理坐标数据"""
    for i in range(0, len(coordinates), batch_size):
        batch = coordinates[i:i + batch_size]
        # 处理批次数据
        yield process_batch(batch)

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    end_time = datetime.now()
    
    logger.info(
        f"Path: {request.url.path} | "
        f"Method: {request.method} | "
        f"Status: {response.status_code} | "
        f"Duration: {(end_time - start_time).total_seconds():.3f}s"
    )
    
    return response

# 错误处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(
        f"HTTP Exception: {exc.status_code} - {exc.detail} | "
        f"Path: {request.url.path}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(
        f"Unhandled Exception: {str(exc)} | "
        f"Path: {request.url.path}",
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

@app.get("/cities")
async def get_cities():
    try:
        logger.info("Fetching cities list")
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT city FROM listings ORDER BY city")
                cities = [row['city'] for row in cur.fetchall()]
                logger.info(f"Found {len(cities)} cities")
                return {"cities": cities}
    except Exception as e:
        logger.error(f"Error in get_cities: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/city/{city_name}")
async def get_city_listings(city_name: str):
    try:
        # 检查缓存
        if city_name in city_cache:
            return city_cache[city_name]

        query = """
            WITH stats AS (
                SELECT 
                    MIN(first_review) as earliest,
                    MAX(first_review) as latest,
                    AVG(ST_Y(geom)) as avg_lat,
                    AVG(ST_X(geom)) as avg_lng,
                    COUNT(*) as total_listings
                FROM listings 
                WHERE city = :city 
                AND first_review IS NOT NULL 
                AND geom IS NOT NULL
            )
            SELECT * FROM stats
        """
        
        result = await database.fetch_one(
            query=query,
            values={"city": city_name}
        )
        
        if not result:
            raise HTTPException(status_code=404, detail=f"City not found: {city_name}")
        
        response_data = {
            "center": {
                "latitude": float(result['avg_lat']),
                "longitude": float(result['avg_lng'])
            },
            "time_window": {
                "earliest": result['earliest'].strftime('%Y-%m-%d') if result['earliest'] else None,
                "latest": result['latest'].strftime('%Y-%m-%d') if result['latest'] else None
            },
            "total_listings": result['total_listings']
        }
        
        # 存入缓存
        city_cache[city_name] = response_data
        return response_data
        
    except Exception as e:
        logger.error(f"Error in get_city_listings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/city/{city_name}/host_ranking")
async def get_host_ranking(city_name: str, time_point: str):
    try:
        target_date = datetime.strptime(time_point, "%Y-%m")
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 获取符合条件的房源数据
                cur.execute("""
                    WITH host_listings AS (
                        SELECT 
                            host_id,
                            COUNT(*) as listing_count
                        FROM listings
                        WHERE city = %s 
                        AND first_review <= %s
                        GROUP BY host_id
                        ORDER BY listing_count DESC
                    )
                    SELECT * FROM host_listings
                """, (city_name, target_date))
                
                results = cur.fetchall()
                if not results:
                    return {
                        "host_categories": {},
                        "total_hosts": 0,
                        "total_listings": 0
                    }
                
                # 转换为 DataFrame 进行分类
                df = pd.DataFrame(results)
                
                # 分类处理
                class_5 = df[df['listing_count'] == 1]
                class_4 = df[df['listing_count'] == 2]
                remaining_hosts = df[df['listing_count'] > 2]
                
                if len(remaining_hosts) > 0:
                    p5_index = max(1, int(len(remaining_hosts) * 0.05))
                    p15_index = max(p5_index + 1, int(len(remaining_hosts) * 0.15))
                    
                    class_1 = remaining_hosts.iloc[:p5_index]
                    class_2 = remaining_hosts.iloc[p5_index:p15_index]
                    class_3 = remaining_hosts.iloc[p15_index:]
                else:
                    class_1 = pd.DataFrame()
                    class_2 = pd.DataFrame()
                    class_3 = pd.DataFrame()
                
                def get_category_info(df):
                    if len(df) == 0:
                        return {
                            "range": None,
                            "count": 0,
                            "host_ids": []
                        }
                    return {
                        "range": {
                            "min": int(df['listing_count'].min()),
                            "max": int(df['listing_count'].max())
                        },
                        "count": len(df),
                        "host_ids": [str(id) for id in df['host_id']]
                    }
                
                host_categories = {
                    "highly_commercial": get_category_info(class_1),
                    "commercial": get_category_info(class_2),
                    "semi_commercial": get_category_info(class_3),
                    "dual_host": get_category_info(class_4),
                    "single_host": get_category_info(class_5)
                }
                
                return {
                    "host_categories": host_categories,
                    "total_hosts": len(df),
                    "total_listings": int(df['listing_count'].sum())
                }
                
    except ValueError as ve:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid time format: {str(ve)}. Please use YYYY-MM format."
        )
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/city/{city_name}/listings_by_categories")
async def get_listings_by_categories(
    city_name: str, 
    time_point: str, 
    categories: str
):
    try:
        target_date = datetime.strptime(time_point, "%Y-%m")
        selected_categories = categories.split(',')
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 获取房东分类
                cur.execute("""
                    WITH host_listings AS (
                        SELECT 
                            host_id,
                            COUNT(*) as listing_count
                        FROM listings
                        WHERE city = %s 
                        AND first_review <= %s
                        GROUP BY host_id
                    )
                    SELECT * FROM host_listings
                    ORDER BY listing_count DESC
                """, (city_name, target_date))
                
                results = cur.fetchall()
                if not results:
                    return {"listings": [], "total_listings": 0}
                
                # 分类房东
                df = pd.DataFrame(results)
                single_hosts = set(df[df['listing_count'] == 1]['host_id'])
                dual_hosts = set(df[df['listing_count'] == 2]['host_id'])
                multi_hosts = df[df['listing_count'] > 2]
                
                selected_hosts = set()
                if len(multi_hosts) > 0:
                    p5_count = max(1, int(len(multi_hosts) * 0.05))
                    p15_count = max(p5_count + 1, int(len(multi_hosts) * 0.15))
                    
                    if 'highly_commercial' in selected_categories:
                        selected_hosts.update(multi_hosts.iloc[:p5_count]['host_id'])
                    if 'commercial' in selected_categories:
                        selected_hosts.update(multi_hosts.iloc[p5_count:p15_count]['host_id'])
                    if 'semi_commercial' in selected_categories:
                        selected_hosts.update(multi_hosts.iloc[p15_count:]['host_id'])
                
                if 'dual_host' in selected_categories:
                    selected_hosts.update(dual_hosts)
                if 'single_host' in selected_categories:
                    selected_hosts.update(single_hosts)
                
                if not selected_hosts:
                    return {"listings": [], "total_listings": 0}
                
                # 获取选中房东的房源
                host_ids = tuple(selected_hosts)
                cur.execute("""
                    SELECT 
                        host_id,
                        latitude,
                        longitude,
                        name,
                        price
                    FROM listings
                    WHERE city = %s 
                    AND first_review <= %s
                    AND host_id = ANY(%s)
                    AND latitude IS NOT NULL
                    AND longitude IS NOT NULL
                """, (city_name, target_date, list(host_ids)))
                
                listings = cur.fetchall()
                return {
                    "listings": listings,
                    "total_listings": len(listings)
                }
                
    except ValueError as ve:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid time format: {str(ve)}. Please use YYYY-MM format."
        )
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/city/{city_name}/hexgrid")
async def get_city_hexgrid(
    city_name: str,
    time_point: str = None,
    categories: str = None,
    view_type: str = 'grid'  # 添加视图类型参数，默认为网格图
):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 构建基础查询
                if time_point and categories:
                    target_date = datetime.strptime(time_point, "%Y-%m")
                    selected_categories = categories.split(',')
                    
                    # 获取符合条件的房东
                    cur.execute("""
                        WITH host_listings AS (
                            SELECT 
                                host_id,
                                COUNT(*) as listing_count
                            FROM listings
                            WHERE city = %s 
                            AND first_review <= %s
                            GROUP BY host_id
                        )
                        SELECT host_id, listing_count
                        FROM host_listings
                        ORDER BY listing_count DESC
                    """, (city_name, target_date))
                    
                    results = cur.fetchall()
                    if results:
                        df = pd.DataFrame(results)
                        selected_hosts = set()
                        
                        # 分类并选择房东
                        single_hosts = set(df[df['listing_count'] == 1]['host_id'])
                        dual_hosts = set(df[df['listing_count'] == 2]['host_id'])
                        multi_hosts = df[df['listing_count'] > 2]
                        
                        if len(multi_hosts) > 0:
                            p5_count = max(1, int(len(multi_hosts) * 0.05))
                            p15_count = max(p5_count + 1, int(len(multi_hosts) * 0.15))
                            
                            if 'highly_commercial' in selected_categories:
                                selected_hosts.update(multi_hosts.iloc[:p5_count]['host_id'])
                            if 'commercial' in selected_categories:
                                selected_hosts.update(multi_hosts.iloc[p5_count:p15_count]['host_id'])
                            if 'semi_commercial' in selected_categories:
                                selected_hosts.update(multi_hosts.iloc[p15_count:]['host_id'])
                        
                        if 'dual_host' in selected_categories:
                            selected_hosts.update(dual_hosts)
                        if 'single_host' in selected_categories:
                            selected_hosts.update(single_hosts)
                        
                        # 使用PostGIS获取坐标
                        if selected_hosts:
                            if view_type == 'scatter':
                                # 对于散点图，获取更多的房源信息
                                cur.execute("""
                                    SELECT 
                                        host_id,
                                        ST_Y(geom) as latitude,
                                        ST_X(geom) as longitude,
                                        name,
                                        price
                                    FROM listings
                                    WHERE city = %s 
                                    AND host_id = ANY(%s)
                                    AND geom IS NOT NULL
                                """, (city_name, list(selected_hosts)))
                            else:
                                # 对于网格图，只需要坐标信息
                                cur.execute("""
                                    SELECT 
                                        ST_Y(geom) as latitude,
                                        ST_X(geom) as longitude
                                    FROM listings
                                    WHERE city = %s 
                                    AND host_id = ANY(%s)
                                    AND geom IS NOT NULL
                                """, (city_name, list(selected_hosts)))
                    else:
                        # 不带筛选的查询
                        if view_type == 'scatter':
                            cur.execute("""
                                SELECT 
                                    host_id,
                                    ST_Y(geom) as latitude,
                                    ST_X(geom) as longitude,
                                    name,
                                    price
                                FROM listings
                                WHERE city = %s
                                AND geom IS NOT NULL
                            """, (city_name,))
                        else:
                            cur.execute("""
                                SELECT 
                                    ST_Y(geom) as latitude,
                                    ST_X(geom) as longitude
                                FROM listings
                                WHERE city = %s
                                AND geom IS NOT NULL
                            """, (city_name,))
                    
                    results = cur.fetchall()
                    
                    if not results:
                        raise HTTPException(status_code=500, detail="No valid coordinates found")
                    
                    if view_type == 'scatter':
                        # 返回散点图数据
                        return {
                            "listings": results,
                            "total_listings": len(results)
                        }
                    
                    # 以下是网格图的处理逻辑
                    # ... (保持原有的网格图处理代码不变)
                    
                    # 获取边界
                    cur.execute("""
                        SELECT 
                            ST_YMin(ST_Collect(geom)) as min_lat,
                            ST_YMax(ST_Collect(geom)) as max_lat,
                            ST_XMin(ST_Collect(geom)) as min_lng,
                            ST_XMax(ST_Collect(geom)) as max_lng
                        FROM listings
                        WHERE city = %s
                        AND geom IS NOT NULL
                    """, (city_name,))
                    
                    bounds_result = cur.fetchone()
                    
                    # 使用H3生成六边形网格
                    coords_df = pd.DataFrame(results)
                    resolution = 9
                    hex_ids = [
                        h3.geo_to_h3(lat, lng, resolution)
                        for lat, lng in coords_df[['latitude', 'longitude']].values
                    ]
                    
                    # 计算每个六边形内的点数
                    hex_counts = Counter(hex_ids)
                    
                    # 生成六边形边界
                    hex_boundaries = []
                    for hex_id, count in hex_counts.items():
                        boundary = h3.h3_to_geo_boundary(hex_id)
                        center = h3.h3_to_geo(hex_id)
                        
                        hex_boundaries.append({
                            'id': str(hex_id),
                            'boundary': [list(point) for point in boundary],
                            'center': list(center),
                            'points_count': count
                        })
                    
                    bounds = {
                        'min_lat': float(bounds_result['min_lat']),
                        'max_lat': float(bounds_result['max_lat']),
                        'min_lng': float(bounds_result['min_lng']),
                        'max_lng': float(bounds_result['max_lng'])
                    }
                    
                    return {
                        'hexagons': hex_boundaries,
                        'bounds': bounds,
                        'total_hexagons': len(hex_counts),
                        'total_points': len(coords_df)
                    }
                    
    except Exception as e:
        print(f"Error generating hexgrid: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/city/{city_name}/yearly_stats")
async def get_yearly_stats(city_name: str):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 进一步优化查询，直接在数据库层计算累计值
                cur.execute("""
                    WITH yearly_data AS (
                        SELECT 
                            host_id,
                            EXTRACT(YEAR FROM first_review) as year,
                            COUNT(*) as listing_count
                        FROM listings
                        WHERE city = %s 
                        AND first_review IS NOT NULL
                        AND EXTRACT(YEAR FROM first_review) IS NOT NULL
                        AND host_id IS NOT NULL
                        GROUP BY host_id, EXTRACT(YEAR FROM first_review)
                    ),
                    cumulative_data AS (
                        SELECT 
                            year,
                            host_id,
                            SUM(listing_count) OVER (
                                PARTITION BY host_id 
                                ORDER BY year
                                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                            ) as cumulative_listings
                        FROM yearly_data
                    ),
                    yearly_summary AS (
                        SELECT 
                            year,
                            host_id,
                            cumulative_listings,
                            ROW_NUMBER() OVER (
                                PARTITION BY year 
                                ORDER BY cumulative_listings DESC
                            ) as rank
                        FROM cumulative_data
                    )
                    SELECT 
                        year,
                        host_id,
                        cumulative_listings,
                        rank
                    FROM yearly_summary
                    ORDER BY year, cumulative_listings DESC
                """, (city_name,))
                
                results = cur.fetchall()
                if not results:
                    return {
                        "yearly_stats": {},
                        "year_range": {
                            "start": None,
                            "end": None
                        }
                    }
                
                # 使用 numpy 加速数据处理
                df = pd.DataFrame(results)
                min_year = int(df['year'].min())
                max_year = int(df['year'].max())
                
                # 预计算年度数据
                yearly_data = {}
                for year in range(min_year + 1, max_year + 1):
                    year_data = df[df['year'] == year].copy()
                    yearly_data[year] = year_data
                
                # 使用 numpy 向量化操作进行分类计算
                @np.vectorize
                def get_host_category(listings):
                    if listings == 1:
                        return 'single'
                    elif listings == 2:
                        return 'dual'
                    else:
                        return 'multi'
                
                # 对每一年进行统计
                yearly_stats = {}
                for year in range(min_year + 1, max_year + 1):
                    year_df = yearly_data[year]
                    
                    # 使用向量化操作进行分类
                    categories = get_host_category(year_df['cumulative_listings'].values)
                    year_df['category'] = categories
                    
                    single_hosts = year_df[year_df['category'] == 'single']
                    dual_hosts = year_df[year_df['category'] == 'dual']
                    multi_hosts = year_df[year_df['category'] == 'multi']
                    
                    stats = {
                        "thresholds": {
                            "single_host": {"min": 1, "max": 1},
                            "dual_host": {"min": 2, "max": 2}
                        },
                        "counts": {
                            "single_host": len(single_hosts),
                            "dual_host": len(dual_hosts)
                        }
                    }
                    
                    # 处理多房源房东
                    if len(multi_hosts) > 0:
                        p5_count = max(1, int(len(multi_hosts) * 0.05))
                        p15_count = max(p5_count + 1, int(len(multi_hosts) * 0.15))
                        
                        highly_commercial = multi_hosts.iloc[:p5_count]
                        commercial = multi_hosts.iloc[p5_count:p15_count]
                        semi_commercial = multi_hosts.iloc[p15_count:]
                        
                        stats["thresholds"].update({
                            "highly_commercial": {
                                "min": int(highly_commercial['cumulative_listings'].min()) if len(highly_commercial) > 0 else None,
                                "max": int(highly_commercial['cumulative_listings'].max()) if len(highly_commercial) > 0 else None
                            },
                            "commercial": {
                                "min": int(commercial['cumulative_listings'].min()) if len(commercial) > 0 else None,
                                "max": int(commercial['cumulative_listings'].max()) if len(commercial) > 0 else None
                            },
                            "semi_commercial": {
                                "min": int(semi_commercial['cumulative_listings'].min()) if len(semi_commercial) > 0 else None,
                                "max": int(semi_commercial['cumulative_listings'].max()) if len(semi_commercial) > 0 else None
                            }
                        })
                        
                        stats["counts"].update({
                            "highly_commercial": len(highly_commercial),
                            "commercial": len(commercial),
                            "semi_commercial": len(semi_commercial)
                        })
                    else:
                        stats["thresholds"].update({
                            "highly_commercial": {"min": None, "max": None},
                            "commercial": {"min": None, "max": None},
                            "semi_commercial": {"min": None, "max": None}
                        })
                        stats["counts"].update({
                            "highly_commercial": 0,
                            "commercial": 0,
                            "semi_commercial": 0
                        })
                    
                    # 计算房东百分比
                    total_hosts = sum(stats["counts"].values())
                    stats["percentages"] = {
                        category: round(count / total_hosts * 100, 2)
                        for category, count in stats["counts"].items()
                    }
                    
                    # 计算房源数量
                    stats["listing_counts"] = {
                        "single_host": len(single_hosts),
                        "dual_host": len(dual_hosts) * 2
                    }
                    
                    if len(multi_hosts) > 0:
                        stats["listing_counts"].update({
                            "highly_commercial": int(highly_commercial['cumulative_listings'].sum()) if len(highly_commercial) > 0 else 0,
                            "commercial": int(commercial['cumulative_listings'].sum()) if len(commercial) > 0 else 0,
                            "semi_commercial": int(semi_commercial['cumulative_listings'].sum()) if len(semi_commercial) > 0 else 0
                        })
                    else:
                        stats["listing_counts"].update({
                            "highly_commercial": 0,
                            "commercial": 0,
                            "semi_commercial": 0
                        })
                    
                    # 计算房源百分比
                    total_listings = sum(stats["listing_counts"].values())
                    stats["listing_percentages"] = {
                        category: round(count / total_listings * 100, 2)
                        for category, count in stats["listing_counts"].items()
                    }
                    
                    yearly_stats[str(year)] = stats
                
                return {
                    "yearly_stats": yearly_stats,
                    "year_range": {
                        "start": min_year + 1,
                        "end": max_year
                    }
                }
                
    except Exception as e:
        print(f"Error generating yearly stats: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/city/{city_name}/listings_by_count")
async def get_listings_by_count(
    city_name: str,
    time_point: str,
    listing_count: int,
    view_type: str  # 'scatter' 或 'grid'
):
    try:
        target_date = datetime.strptime(time_point, "%Y-%m")
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 获取符合条件的房东
                cur.execute("""
                    WITH host_listings AS (
                        SELECT 
                            host_id,
                            COUNT(*) as listing_count
                        FROM listings
                        WHERE city = %s 
                        AND first_review <= %s
                        GROUP BY host_id
                        HAVING COUNT(*) >= %s
                    )
                    SELECT l.host_id, ST_Y(l.geom) as latitude, ST_X(l.geom) as longitude
                    FROM listings l
                    JOIN host_listings h ON l.host_id = h.host_id
                    WHERE l.city = %s 
                    AND l.first_review <= %s
                    AND l.geom IS NOT NULL
                """, (city_name, target_date, listing_count, city_name, target_date))
                
                results = cur.fetchall()
                
                if not results:
                    return {"listings": [], "total_listings": 0}
                
                if view_type == 'scatter':
                    # 返回散点图数据
                    return {
                        "listings": results,
                        "total_listings": len(results)
                    }
                else:
                    # 返回网格图数据
                    coords_df = pd.DataFrame(results)
                    resolution = 9
                    hex_ids = [
                        h3.geo_to_h3(lat, lng, resolution)
                        for lat, lng in coords_df[['latitude', 'longitude']].values
                    ]
                    
                    hex_counts = Counter(hex_ids)
                    hex_boundaries = []
                    
                    for hex_id, count in hex_counts.items():
                        boundary = h3.h3_to_geo_boundary(hex_id)
                        center = h3.h3_to_geo(hex_id)
                        
                        hex_boundaries.append({
                            'id': str(hex_id),
                            'boundary': [list(point) for point in boundary],
                            'center': list(center),
                            'points_count': count
                        })
                    
                    # 获取边界
                    cur.execute("""
                        SELECT 
                            ST_YMin(ST_Collect(geom)) as min_lat,
                            ST_YMax(ST_Collect(geom)) as max_lat,
                            ST_XMin(ST_Collect(geom)) as min_lng,
                            ST_XMax(ST_Collect(geom)) as max_lng
                        FROM listings
                        WHERE city = %s
                        AND geom IS NOT NULL
                    """, (city_name,))
                    
                    bounds_result = cur.fetchone()
                    bounds = {
                        'min_lat': float(bounds_result['min_lat']),
                        'max_lat': float(bounds_result['max_lat']),
                        'min_lng': float(bounds_result['min_lng']),
                        'max_lng': float(bounds_result['max_lng'])
                    }
                    
                    return {
                        'hexagons': hex_boundaries,
                        'bounds': bounds,
                        'total_hexagons': len(hex_counts),
                        'total_points': len(coords_df)
                    }
                
    except ValueError as ve:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid parameter: {str(ve)}"
        )
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/city/{city_name}/updates")
async def get_city_updates(
    city_name: str,
    last_update: datetime = None
):
    """只返回上次更新后变化的数据"""
    if not last_update:
        return await get_city_listings(city_name)
        
    query = """
        SELECT *
        FROM listings
        WHERE city = :city
        AND updated_at > :last_update
    """
    updates = await database.fetch_all(
        query=query,
        values={"city": city_name, "last_update": last_update}
    )
    return {"updates": updates}
