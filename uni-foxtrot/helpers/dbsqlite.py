import sqlite3
import time
import logging

# SQLite database file
db_file = "db/uni-foxtrot.db"

"""
A function that checks the connection to the SQLite database.
"""
def check_connection(attempts=3, delay=5):
    global db_conn
    try:
        db_conn = sqlite3.connect(db_file, check_same_thread=False, detect_types=sqlite3.PARSE_DECLTYPES)
        db_conn.row_factory = sqlite3.Row
        return True
    except sqlite3.Error as e:
        if attempts > 1:
            print(f"Attempt {attempts} failed: {e}")
            time.sleep(delay)
            return check_connection(attempts-1, delay)
        else:
            print(f"Failed to connect after {attempts} attempts: {e}")
            return False


"""
The main function that executes the SQL query and returns the result. If the query is a SELECT statement, it returns the result as a list of rows. If the query is an INSERT statement, it returns the last row ID. If the query is a PRAGMA statement, it returns the result as a list of rows. And finally, it commits the transaction and closes the cursor.
"""
def sql(query, params=(), single=False):
    global db_conn
    query = query.replace("%s", "?")
    # print(f"Query: {query}, Params: {params}")

    try:
        if not check_connection():
            logging.basicConfig(filename='sqlite.log', level=logging.INFO)
            logging.error('Error connecting to the database from Python application call: GROQ')

        cursor = db_conn.cursor()
        cursor.execute(query, params)

        if query.lower().strip().startswith("select"):
            
            if single:
                return convert_sql_to_list(cursor.fetchone(), single=True)
            else:
                return convert_sql_to_list(cursor.fetchall())

        if query.lower().strip().startswith("pragma"):
            
            if single:
                return convert_sql_to_list(cursor.fetchone(), single=True)
            else:
                return convert_sql_to_list(cursor.fetchall())
            
        elif query.lower().strip().startswith("insert"):
            
            return cursor.lastrowid
        
        else:
            
            return None
        
    finally:
        cursor.close()
        db_conn.commit()


def convert_sql_to_list(sql_result, single=False):
    """
    Converts the SQL result to a list of dictionaries.
    """
    if not sql_result:
        return []

    if single:
        return dict(sql_result)

    result_list = []
    for row in sql_result:
        result_list.append(dict(row))
    return result_list 


"""
The function to connect to the SQLite database. It sets the global variable db_conn to the connection object.
"""
def connect_db():
    global db_conn
    try:
        db_conn = sqlite3.connect(db_file, check_same_thread=False)
        db_conn.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        print(f"Error connecting to the database: {e}")
        db_conn = None
        return False


"""
Function to close the database connection.
"""
def close_db():
    global db_conn
    if db_conn is not None:
        db_conn.close()
