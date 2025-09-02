import os
import psycopg2
from dotenv import load_dotenv

def get_connection():
    """Establishes a database connection using credentials from .env file."""
    dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../temp/.env'))
    load_dotenv(dotenv_path=dotenv_path)

    jdbc_url = os.getenv("DB_CONNECTION_STRING")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    if not all([jdbc_url, db_user, db_password]):
        raise ValueError("Database credentials not found in temp/.env")

    url_body = jdbc_url.replace('jdbc:postgresql://', '').split('?')[0]
    parts = url_body.split('/')
    host_port_str, db_name = parts[0], parts[1]
    host, port = host_port_str.split(':')
    sslmode = 'require' if 'sslmode=require' in jdbc_url else 'allow'

    return psycopg2.connect(
        dbname=db_name, user=db_user, password=db_password,
        host=host, port=port, sslmode=sslmode
    )

def solve_quiz(question: str, choices: list = None):
    """
    Finds the correct answer to a quiz question from the database.
    """
    print(f"[Quiz Solver Tool] Received question: \"{question}\"")
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        SELECT
            ans.answer
        FROM
            answers AS ans
        JOIN
            question_answers AS qa ON ans.id = qa.answer_id
        JOIN
            questions AS q ON qa.question_id = q.id
        WHERE
            q.question = %s AND qa.is_correct = TRUE;
        """
        cursor.execute(query, (question,))
        result = cursor.fetchone()
        answer = result[0] if result else None

        cursor.close()
        conn.close()

        if answer:
            print(f"[Quiz Solver Tool] Found answer: \"{answer}\"")
            return answer
        else:
            print("[Quiz Solver Tool] Answer not found in the database.")
            return "Answer not found."

    except Exception as e:
        error_message = f"[Quiz Solver Tool] An error occurred: {e}"
        print(error_message)
        return error_message