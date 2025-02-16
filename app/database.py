from pymongo import MongoClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os

# ✅ MySQL Configuration (Users & Admin Data)
# MYSQL_DB_URL = os.getenv("MYSQL_DB_URL", "mysql+pymysql://user:password@mysql_host/dseu_main")
# mysql_engine = create_engine(MYSQL_DB_URL, pool_recycle=3600)
# SQLSessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=mysql_engine))

# def get_mysql_db():
#     """Dependency to get MySQL session."""
#     db = SQLSessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# ✅ MongoDB Configuration (Primary Storage for Attendance & Inventory)
MONGO_DB_URL = os.getenv("MONGO_DB_URL", "mongodb+srv://dseu_admin:dseu_admin@dseu-cluster.plm4o.mongodb.net/?retryWrites=true&w=majority&appName=DSEU-Cluster")
mongo_client = MongoClient(MONGO_DB_URL)
mongo_db = mongo_client["dseu_main"]  # Use `dseu_main` database

def get_mongo_db():
    """Returns the MongoDB database connection."""
    return mongo_db

def get_mongo_collection(collection_name):
    """Returns a specific MongoDB collection."""
    return mongo_db[collection_name]
