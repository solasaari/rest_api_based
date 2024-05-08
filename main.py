import os
import sqlite3

from flask import Flask, jsonify, json, request, g

app = Flask(__name__)
DATABASE = "tasks.db"


# Function to get a database connection
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


# Initialize the database
def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource("schema.sql", mode="r") as f:
            db.cursor().executescript(f.read())
        db.commit()


# Close the database connection when the application ends
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


# Get a database connection and cursor for each request
@app.before_request
def before_request():
    g.db = get_db()
    g.cursor = g.db.cursor()


# Close the cursor after each request
@app.teardown_request
def teardown_request(exception):
    cursor = getattr(g, "cursor", None)
    if cursor is not None:
        cursor.close()


# To test that the dev server is running
@app.route("/")
def hello():
    return "<p>Hello!</p>"


# Get number of total tasks and closed tasks for a user
@app.route("/rest_api_based/tasks/counter/<int:user_id>", methods=["GET"])
def get_tasks_counter(user_id):
    g.cursor.execute(
        "SELECT COUNT(*), SUM(is_closed) FROM tasks_data WHERE user_id=?", (user_id,)
    )
    tasks_created, tasks_closed = g.cursor.fetchone()
    return jsonify({"tasks_created": tasks_created, "tasks_closed": tasks_closed})


# Get number of tasks in progress for a user
@app.route("/rest_api_based/tasks/in_progress/<int:user_id>", methods=["GET"])
def get_tasks_in_progress(user_id):
    g.cursor.execute(
        "SELECT COUNT(*) FROM tasks_data WHERE user_id=? AND is_closed=0", (user_id,)
    )
    tasks_count = g.cursor.fetchone()[0]
    return jsonify({"tasks_in_progress": tasks_count})


# Handle adding tasks to the db
@app.route("/rest_api_based/tasks/add_task/<int:user_id>", methods=["POST"])
def add_task(user_id):
    if request.is_json:
        task_data = request.json
    else:
        task_data = json.loads(request.data)

    if len(task_data) > 5:
        return (
            jsonify(
                {
                    "message": "Not so fast, cowboy! Only 1 to 5 tasks supported in one request"
                }
            ),
            400,
        )

    for task in task_data:
        current_task_count = get_tasks_in_progress(user_id).json["tasks_in_progress"]
        if current_task_count >= 10:
            # Mark the oldest task as closed
            g.cursor.execute(
                "UPDATE tasks_data SET is_closed=1 WHERE user_id=? AND is_closed=0 ORDER BY task_id ASC LIMIT 1",
                (user_id,),
            )
            g.db.commit()

        g.cursor.execute(
            "INSERT INTO tasks_data (user_id, task_description, is_closed) VALUES (?, ?, ?)",
            (
                user_id,
                task.get("task_description"),
                0,
            ),
        )
        g.db.commit()

    return jsonify({"message": "Tasks added successfully"}), 201


# Close specific task (requires task id)
@app.route(
    "/rest_api_based/tasks/close_task/<int:user_id>/<int:task_id>", methods=["PUT"]
)
def close_task(user_id, task_id):
    g.cursor.execute(
        "UPDATE tasks_data SET is_closed=1 WHERE user_id=? AND task_id=?",
        (user_id, task_id),
    )
    g.db.commit()
    return jsonify({"message": "Task closed successfully"})


# Delete specific task (requires task id)
@app.route(
    "/rest_api_based/tasks/delete_task/<int:user_id>/<int:task_id>", methods=["DELETE"]
)
def delete_task(user_id, task_id):
    # Check if the task exists before attempting deletion
    g.cursor.execute(
        "SELECT * FROM tasks_data WHERE user_id=? AND task_id=?", (user_id, task_id)
    )
    task = g.cursor.fetchone()
    if not task:
        return jsonify({"error": "Task not found"}), 404
    # Delete the task if confirmed
    g.cursor.execute(
        "DELETE FROM tasks_data WHERE user_id=? AND task_id=?", (user_id, task_id)
    )
    g.db.commit()
    return jsonify({"message": "Task removed successfully"})


if not os.path.exists(DATABASE):
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
