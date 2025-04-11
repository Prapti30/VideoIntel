import snowflake.connector

def get_snowflake_connection():
    # Replace with your credentials
    conn = snowflake.connector.connect(
        user='PRAPTI30',
        password='Prapti@30082002',
        account='QNQBPTL-USB04850',
        warehouse='COMPUTE_WH',
        database='VIDEOINTEL',
        schema='VIDEOINTEL1'
    )
    return conn

get_snowflake_connection()