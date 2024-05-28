import flask
from flask import Flask, request, jsonify, current_app
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import jwt
import datetime
from datetime import datetime, timedelta
from functools import wraps

app = flask.Flask(__name__)
logging.basicConfig(level=logging.DEBUG)  # Set the logging level to DEBUG
app.logger.setLevel(logging.DEBUG)  # Ensure the Flask app's logger is also set to DEBUG

StatusCodes = {"success": 200, "api_error": 400, "internal_error": 500}

##########################################################
## DATABASE ACCESS
##########################################################


def db_connection():
    db = psycopg2.connect(
        user="aulaspl",
        password="aulaspl",
        host="127.0.0.1",
        port="5432",
        database="projeto2024",
    )

    return db


##########################################################
## ENDPOINTS
##########################################################


@app.route("/")
def hello():
    app.logger.debug("This is a debug message")
    return "Hello World!"


@app.route("/dbproj/register/<user_type>", methods=["POST"])
def register_user(user_type):
    # Check if the request has a JSON body
    if not request.json:
        return (
            jsonify({"status": 400, "errors": "Bad request, JSON data is required"}),
            400,
        )

    data = request.json

    # Common attributes
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")  # Remember to hash passwords before storing them!

    # Additional attributes for user profiles
    name = data.get("name")
    date_of_birth = data.get("date_of_birth")
    address = data.get("address")
    phone_number = data.get("phone_number")
    contract_details = data.get("contract_details", None)  # Potentially optional

    # Doctor-specific attributes
    medical_license = data.get("medical_license", None)
    specialization_name = data.get("specialization_name", None)
    specialization_id = data.get("specialization_id", None)

    # Nurse-specific attributes
    hierarchical_category = data.get("hierarchical_category", None)

    # Connect to the database
    conn = db_connection()
    cursor = conn.cursor()

    try:
        if user_type == "doctor":
            if not all([medical_license, specialization_name, specialization_id]):
                return (
                    jsonify(
                        {
                            "status": 400,
                            "errors": "Missing fields for doctor registration",
                        }
                    ),
                    400,
                )

            # Insert doctor with all the required details
            user_id = insert_doctor(
                cursor,
                username,
                email,
                password,
                name,
                date_of_birth,
                address,
                phone_number,
                contract_details,
                medical_license,
                specialization_id,
                specialization_name,
            )
        elif user_type == "patient":
            # Insert patient with all the required details
            medical_history = data.get("medical_history")
            user_id = insert_patient(
                cursor,
                username,
                email,
                password,
                name,
                date_of_birth,
                address,
                phone_number,
                medical_history,
            )
        elif user_type == "nurse":
            # Insert nurse with all the required details
            user_id = insert_nurse(
                cursor,
                username,
                email,
                password,
                name,
                date_of_birth,
                address,
                phone_number,
                contract_details,
                hierarchical_category,
            )
        elif user_type == "assistant":
            # Insert assistant with all the required details
            user_id = insert_assistant(
                cursor,
                username,
                email,
                password,
                name,
                date_of_birth,
                address,
                phone_number,
                contract_details,
            )

        conn.commit()
        return jsonify({"status": 200, "results": user_id}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"status": 500, "errors": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


def insert_user(
    cursor,
    user_type,
    username,
    email,
    password,
    name,
    date_of_birth,
    address,
    phone_number,
    contract_details,
):
    # Insert into the employee table and get the employee_id
    employee_sql = """
    INSERT INTO employee (username, email, password, name, date_of_birth, address, phone_number, contract_details)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING employee_id;
    """
    cursor.execute(
        employee_sql,
        (
            username,
            email,
            password,
            name,
            date_of_birth,
            address,
            phone_number,
            contract_details,
        ),
    )
    employee_id = cursor.fetchone()[0]

    # Logic for different user types can be added here
    # if user_type == 'nurse': # Similar to the doctor, but with nurse-specific details

    return employee_id


def insert_doctor(
    cursor,
    username,
    email,
    password,
    name,
    date_of_birth,
    address,
    phone_number,
    contract_details,
    medical_license,
    specialization_id,
    specialization_name,
):
    # First, insert the doctor as an employee to get the employee_id
    employee_id = insert_user(
        cursor,
        "doctor",
        username,
        email,
        password,
        name,
        date_of_birth,
        address,
        phone_number,
        contract_details,
    )

    # Then, insert the doctor's specialization details
    doctor_sql = """
    INSERT INTO doctor_specialization (medical_license_, specialization_specialization_id, specialization_name, employee_employee_id)
    VALUES (%s, %s, %s, %s);
    """
    cursor.execute(
        doctor_sql,
        (medical_license, specialization_id, specialization_name, employee_id),
    )

    return employee_id


def insert_nurse(
    cursor,
    username,
    email,
    password,
    name,
    date_of_birth,
    address,
    phone_number,
    contract_details,
    hierarchical_category,
):
    # Insert employee and get the employee_id
    employee_id = insert_user(
        cursor,
        "nurse",
        username,
        email,
        password,
        name,
        date_of_birth,
        address,
        phone_number,
        contract_details,
    )

    # Insert nurse specific details
    cursor.execute(
        """
        INSERT INTO nurse (hierarchical_category, employee_employee_id)
        VALUES (%s, %s);
    """,
        (hierarchical_category, employee_id),
    )

    return employee_id


def insert_assistant(
    cursor,
    username,
    email,
    password,
    name,
    date_of_birth,
    address,
    phone_number,
    contract_details,
):
    # Insert employee and get the employee_id
    employee_id = insert_user(
        cursor,
        "assistant",
        username,
        email,
        password,
        name,
        date_of_birth,
        address,
        phone_number,
        contract_details,
    )

    # Insert assistant into the database
    cursor.execute(
        """
        INSERT INTO assistant (employee_employee_id)
        VALUES (%s);
    """,
        (employee_id,),
    )

    return employee_id


def insert_patient(
    cursor,
    username,
    email,
    password,
    name,
    date_of_birth,
    address,
    phone_number,
    medical_history,
):
    try:
        # Insert patient into the database
        cursor.execute(
            """
            INSERT INTO patient (username, email, password, name, date_of_birth, address, phone_number, medical_history)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING patient_id;
        """,
            (
                username,
                email,
                password,
                name,
                date_of_birth,
                address,
                phone_number,
                medical_history,
            ),
        )
        patient_id = cursor.fetchone()[0]

        return patient_id
    except Exception as e:
        raise e


# Secret key to encode the JWT
app.config["SECRET_KEY"] = "your_secret_key"


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            token = request.headers["Authorization"].split(" ")[
                1
            ]  # Authorization: Bearer <token>
        if not token:
            return jsonify({"status": 401, "message": "Token is missing!"}), 401
        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        except:
            return jsonify({"status": 403, "message": "Token is invalid!"}), 403
        return f(*args, **kwargs)

    return decorated


def check_user(username, password):
    """Check if the user exists and the password is correct in the employee and patient tables."""
    conn = db_connection()
    cursor = conn.cursor()
    try:
        # SQL statement to execute
        # Check the employee table
        cursor.execute(
            "SELECT password FROM employee WHERE username = %s;", (username,)
        )
        employee_password = cursor.fetchone()

        # If not found in employee, check in patient
        if employee_password is None:
            cursor.execute(
                "SELECT password FROM patient WHERE username = %s;", (username,)
            )
            patient_password = cursor.fetchone()
            if patient_password is None:
                return False  # Username not found in both tables

            # Assume passwords are stored in plain text (not secure, use hashed passwords instead)
            return password == patient_password[0]

        # Check the retrieved password
        return password == employee_password[0]

    except Exception as e:
        print(f"Database error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


@app.route("/dbproj/user", methods=["PUT"])
def login():
    auth = request.json
    if not auth or not auth.get("username") or not auth.get("password"):
        return jsonify({"status": 400, "errors": "Username or password missing"}), 400
    user = check_user(auth.get("username"), auth.get("password"))
    if not user:
        return jsonify({"status": 401, "errors": "Invalid Credentials"}), 401
    # Generate a JWT token
    token = jwt.encode(
        {
            "user": auth.get("username"),
            "exp": datetime.utcnow() + timedelta(hours=1),  # Token expires in 1 hour
        },
        app.config["SECRET_KEY"],
        algorithm="HS256",
    )
    return jsonify({"status": 200, "results": token}), 200


# Example protected route
@app.route("/dbproj/protected", methods=["GET"])
@token_required
def protected():
    return jsonify({"message": "This is only available for people with valid tokens."})


def decode_token(token):
    try:
        decoded = jwt.decode(
            token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
        )
        app.logger.debug(f"Token payload: {decoded}")
        username = decoded.get("user")
        if username is None:
            app.logger.debug("User key is missing from the token payload")
            return None
        return username
    except jwt.ExpiredSignatureError:
        app.logger.debug("Token has expired")
        return None
    except jwt.InvalidTokenError:
        app.logger.debug("Invalid token")
        return None
    except Exception as e:
        app.logger.error(f"Unexpected error decoding token: {str(e)}")
        return None


@app.route("/dbproj/appointment", methods=["POST"])
def schedule_appointment():
    if (
        not request.json
        or "doctor_id" not in request.json
        or "date" not in request.json
    ):
        return jsonify({"status": 400, "errors": "Missing required fields"}), 400

    doctor_id = request.json["doctor_id"]
    date = request.json["date"]
    purpose = request.json.get("purpose", None)  # 'purpose' is optional

    token = (
        request.headers.get("Authorization", "").split(" ")[1]
        if "Authorization" in request.headers
        else None
    )
    if token:
        username = decode_token(token)
        app.logger.debug(f"Decoded username: {username}")
        if not username:
            return jsonify({"status": 403, "errors": "Invalid or expired token"}), 403

        # Query the database for the patient_id using the username
        try:
            conn = db_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT patient_id FROM patient WHERE username = %s", (username,)
            )
            patient_id = cur.fetchone()
            if patient_id is None:
                return (
                    jsonify(
                        {
                            "status": 404,
                            "errors": "No patient found with the given username",
                        }
                    ),
                    404,
                )
            patient_id = patient_id[0]
        except psycopg2.Error as e:
            conn.rollback()
            return jsonify({"status": 500, "errors": str(e)}), 500
        finally:
            cur.close()
            conn.close()
    else:
        return jsonify({"status": 401, "errors": "Unauthorized access"}), 401

    try:
        conn = db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO appointment (doctor_specialization_employee_employee_id, patient_patient_id, date_appointment, purpose) 
            VALUES (%s, %s, %s, %s) RETURNING appointment_id;
        """,
            (doctor_id, patient_id, date, purpose),
        )  # Include purpose in the insert statement
        appointment_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({"status": 200, "results": appointment_id}), 200
    except psycopg2.Error as e:
        conn.rollback()
        return jsonify({"status": 500, "errors": str(e)}), 500
    finally:
        cur.close()
        conn.close()


def get_user_role_and_id_from_token(token):
    """
    Function to retrieve the user's role and ID from the token.
    """
    try:
        # Decode the token to get user details
        user_info = jwt.decode(
            token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
        )
        username = user_info.get("user", None)  # Retrieve the username from the token

        # Query the database to check if the username belongs to a patient
        conn = db_connection()
        cursor = conn.cursor()

        # Check if the username belongs to a patient
        cursor.execute(
            "SELECT patient_id FROM patient WHERE username = %s;", (username,)
        )
        patient_id = cursor.fetchone()

        if patient_id:  # If the username belongs to a patient
            cursor.close()
            conn.close()
            return "patient", patient_id[0]  # Return role as 'patient' and patient_id

        else:  # If the username does not belong to a patient, check if it belongs to an employee
            # Check if the username belongs to an employee
            cursor.execute(
                "SELECT employee_id FROM employee WHERE username = %s;", (username,)
            )
            employee_id = cursor.fetchone()

            if employee_id:  # If the username belongs to an employee
                # Further query to determine the employee's role
                # Check if the employee is a doctor
                cursor.execute(
                    "SELECT employee_employee_id FROM doctor_specialization WHERE employee_employee_id = %s;",
                    (employee_id[0],),
                )
                doctor_id = cursor.fetchone()

                if doctor_id:  # If the employee is a doctor
                    cursor.close()
                    conn.close()
                    return (
                        "doctor",
                        doctor_id[0],
                    )  # Return role as 'doctor' and doctor_id

                # Check if the employee is a nurse
                cursor.execute(
                    "SELECT employee_employee_id FROM nurse WHERE employee_employee_id = %s;",
                    (employee_id[0],),
                )
                nurse_id = cursor.fetchone()

                if nurse_id:  # If the employee is a nurse
                    cursor.close()
                    conn.close()
                    return "nurse", nurse_id[0]  # Return role as 'nurse' and nurse_id

                # Check if the employee is an assistant
                cursor.execute(
                    "SELECT employee_employee_id FROM assistant WHERE employee_employee_id = %s;",
                    (employee_id[0],),
                )
                assistant_id = cursor.fetchone()

                if assistant_id:  # If the employee is an assistant
                    cursor.close()
                    conn.close()
                    return (
                        "assistant",
                        assistant_id[0],
                    )  # Return role as 'assistant' and assistant_id

                # If the employee is not a doctor, nurse, or assistant
                cursor.close()
                conn.close()
                return None, None

            else:  # If the username does not belong to a patient or an employee
                cursor.close()
                conn.close()
                return None, None

    except jwt.ExpiredSignatureError:
        app.logger.debug("Token has expired")
        return None, None
    except jwt.InvalidTokenError:
        app.logger.debug("Invalid token")
        return None, None
    except Exception as e:
        app.logger.error(f"Unexpected error decoding token: {str(e)}")
        return None, None


@app.route("/dbproj/appointments/<int:patient_user_id>", methods=["GET"])
@token_required  # This decorator must check the token validity before proceeding
def see_appointments(patient_user_id):
    token = request.headers.get("Authorization", "").split(" ")[1]
    user_role, user_id = get_user_role_and_id_from_token(token)

    # Check if the user is authorized to access the endpoint
    if user_role not in ["assistant", "patient"] or (
        user_role == "patient" and user_id != patient_user_id
    ):
        return (
            jsonify(
                {
                    "status": 403,
                    "errors": "You are not authorized to view these appointments",
                }
            ),
            403,
        )

    # Query the database for appointments if the user is authorized
    conn = db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT a.appointment_id, a.doctor_specialization_employee_employee_id, a.date_appointment, d.name
            FROM appointment a
            JOIN doctor_specialization ds ON a.doctor_specialization_employee_employee_id = ds.employee_employee_id
            JOIN employee d ON ds.employee_employee_id = d.employee_id
            WHERE a.patient_patient_id = %s
        """,
            (patient_user_id,),
        )
        appointments = cursor.fetchall()

        # Format the results
        results = [
            {
                "id": appt[0],
                "doctor_id": appt[1],
                "date": appt[2].strftime("%Y-%m-%d"),
                "doctor_name": appt[3],
            }
            for appt in appointments
        ]
        return jsonify({"status": 200, "results": results}), 200

    except psycopg2.Error as e:
        return jsonify({"status": 500, "errors": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route("/dbproj/surgery", methods=["POST"])
@app.route("/dbproj/surgery/<int:hospitalization_id>", methods=["POST"])
def schedule_surgery(hospitalization_id=None):
    token = request.headers.get("Authorization", "").split(" ")[1]
    if not token:
        return jsonify({"status": 403, "errors": "No token provided"}), 403

    user_role, user_id = get_user_role_and_id_from_token(token)
    app.logger.debug(f"User role from token: {user_role}")

    if user_role != "assistant":
        return jsonify({"status": 403, "errors": "Unauthorized access"}), 403

    data = request.json
    patient_id = data["patient_id"]
    doctor_specialization_id = data["doctor"]
    nurses = data["nurses"]
    date_surgery = data["date"]

    conn = db_connection()
    cursor = conn.cursor()

    try:
        conn.autocommit = False  # Start transaction

        # Create new billing record and get bill_id
        cursor.execute(
            "INSERT INTO bill_ (total_amount, status_) VALUES (%s, %s) RETURNING bill_id;",
            (1000, False),
        )
        bill_id = cursor.fetchone()[0]

        if not hospitalization_id:
            # Assuming the first nurse in the list is the primary nurse for this hospitalization
            primary_nurse_id = nurses[0][0] if nurses else None
            if not primary_nurse_id:
                return (
                    jsonify({"status": 400, "errors": "No primary nurse provided"}),
                    400,
                )

            # Create new hospitalization with the new bill_id and primary nurse id
            cursor.execute(
                "INSERT INTO hospitalization (patient_patient_id, admission_date, nurse_employee_employee_id, bill__bill_id) VALUES (%s, %s, %s, %s) RETURNING hospitalization_id;",
                (patient_id, date_surgery, primary_nurse_id, bill_id),
            )
            hospitalization_id = cursor.fetchone()[0]

        # Insert new surgery
        cursor.execute(
            "INSERT INTO surgery (doctor_specialization_employee_employee_id, hospitalization_hospitalization_id, date_surgery) VALUES (%s, %s, %s) RETURNING surgery_id;",
            (doctor_specialization_id, hospitalization_id, date_surgery),
        )
        surgery_id = cursor.fetchone()[0]

        # Associate nurses with the surgery
        for nurse in nurses:
            cursor.execute(
                "INSERT INTO nurse_surgery (nurse_employee_employee_id, surgery_surgery_id) VALUES (%s, %s);",
                (nurse[0], surgery_id),
            )

        conn.commit()  # Commit transaction if everything is successful

        response = {
            "status": 200,
            "results": {
                "hospitalization_id": hospitalization_id,
                "surgery_id": surgery_id,
                "patient_id": patient_id,
                "doctor_specialization_employee_employee_id": doctor_specialization_id,
                "date_surgery": date_surgery,
                "bill_id": bill_id,  # Include the bill_id in the response
            },
        }
    except Exception as e:
        conn.rollback()  # Rollback the transaction on any error
        response = {"status": 500, "errors": str(e)}
    finally:
        conn.autocommit = True  # Reset autocommit setting
        cursor.close()
        conn.close()

    return jsonify(response), response["status"]


@app.route("/dbproj/prescriptions/<int:person_id>", methods=["GET"])
@token_required
def get_prescriptions(person_id):
    # Check if the requester is an assistant or the targeted patient
    token = request.headers.get("Authorization", "").split(" ")[1]
    user_role, user_id = get_user_role_and_id_from_token(token)
    if user_role not in ["assistant", "patient"] or (
        user_role == "patient" and user_id != person_id
    ):
        return jsonify({"status": 403, "errors": "Unauthorized access"}), 403

    conn = db_connection()
    if not conn:
        return jsonify({"status": 500, "errors": "Database connection failed"}), 500

    try:
        cursor = conn.cursor()
        # Fetch prescriptions linked to both appointments and hospitalizations
        cursor.execute(
            """
            SELECT DISTINCT p.prescription_id_, p.validity, po.dosage, po.frequency, m.name as medicine
            FROM Prescription p
            JOIN Posology po ON p.prescription_id_ = po.prescription_prescription_id_
            JOIN Medicine m ON po.medicine_medicine_id = m.medicine_id
            LEFT JOIN Appointment_Prescription ap ON ap.prescription_prescription_id_ = p.prescription_id_
            LEFT JOIN Appointment a ON ap.appointment_appointment_id = a.appointment_id AND a.patient_patient_id = %s
            LEFT JOIN Hospitalization_Prescription hp ON hp.prescription_prescription_id_ = p.prescription_id_
            LEFT JOIN Hospitalization h ON hp.hospitalization_hospitalization_id = h.hospitalization_id AND h.patient_patient_id = %s
            WHERE a.patient_patient_id IS NOT NULL OR h.patient_patient_id IS NOT NULL;
        """,
            (person_id, person_id),
        )
        rows = cursor.fetchall()

        prescriptions = [
            {
                "id": row[0],
                "validity": row[1],
                "posology": {"dose": row[2], "frequency": row[3], "medicine": row[4]},
            }
            for row in rows
        ]

        cursor.close()
        conn.close()

        if not prescriptions:
            return (
                jsonify(
                    {"status": 404, "errors": "No prescriptions found", "results": []}
                ),
                404,
            )

        return jsonify({"status": 200, "results": prescriptions}), 200

    except Exception as e:
        conn.close()
        return jsonify({"status": 500, "errors": str(e)}), 500


@app.route("/dbproj/prescription/", methods=["POST"])
@token_required
def add_prescription():
    # Check if the requester is a doctor
    token = request.headers.get("Authorization", "").split(" ")[1]
    user_role, user_id = get_user_role_and_id_from_token(token)
    if user_role != "doctor":
        return (
            jsonify(
                {
                    "status": 403,
                    "errors": "Unauthorized access, only doctors can use this endpoint",
                }
            ),
            403,
        )

    # Ensure JSON data is provided
    data = request.json
    if (
        not data
        or "type" not in data
        or "event_id" not in data
        or "validity" not in data
        or "medicines" not in data
    ):
        return jsonify({"status": 400, "errors": "Missing required fields"}), 400

    event_type = data["type"]
    event_id = data["event_id"]
    validity = data["validity"]
    medicines = data["medicines"]

    conn = db_connection()
    cursor = conn.cursor()
    try:
        # Begin transaction
        conn.autocommit = False

        # Insert prescription
        cursor.execute(
            """
            INSERT INTO Prescription (validity)
            VALUES (%s) RETURNING prescription_id_;
        """,
            (validity,),
        )
        prescription_id = cursor.fetchone()[0]

        # Check each medicine and insert posology
        for medicine in medicines:
            # Check if medicine exists in the database
            cursor.execute(
                """
                SELECT medicine_id FROM Medicine WHERE name = %s;
            """,
                (medicine["medicine"],),
            )
            result = cursor.fetchone()

            if not result:
                conn.rollback()  # Rollback any changes if medicine is not found
                return (
                    jsonify(
                        {
                            "status": 404,
                            "errors": f"Medicine not found in the database: {medicine['medicine']}",
                        }
                    ),
                    404,
                )

            medicine_id = result[0]

            # Insert into posology
            cursor.execute(
                """
                INSERT INTO Posology (prescription_prescription_id_, dosage, frequency, medicine_medicine_id)
                VALUES (%s, %s, %s, %s);
            """,
                (
                    prescription_id,
                    medicine["posology_dose"],
                    medicine["posology_frequency"],
                    medicine_id,
                ),
            )

        # Link prescription to the event
        if event_type == "appointment":
            cursor.execute(
                """
                INSERT INTO Appointment_Prescription (appointment_appointment_ID, prescription_prescription_ID_)
                VALUES (%s, %s);
            """,
                (event_id, prescription_id),
            )
        elif event_type == "hospitalization":
            cursor.execute(
                """
                INSERT INTO Hospitalization_Prescription (hospitalization_hospitalization_ID, prescription_prescription_ID_)
                VALUES (%s, %s);
            """,
                (event_id, prescription_id),
            )
        else:
            conn.rollback()
            return jsonify({"status": 400, "errors": "Invalid event type"}), 400

        # Commit transaction
        conn.commit()
        return jsonify({"status": 200, "results": prescription_id}), 200
    except Exception as e:
        # Rollback on error
        conn.rollback()
        return jsonify({"status": 500, "errors": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route("/dbproj/bills/<int:bill_id>", methods=["POST"])
@token_required
def execute_payment(bill_id):
    # Ensure that the requester is a patient and the owner of the bill
    token = request.headers.get("Authorization", "").split(" ")[1]
    user_role, patient_id = get_user_role_and_id_from_token(token)
    if user_role != "patient":
        return (
            jsonify(
                {
                    "status": 403,
                    "errors": "Unauthorized access, only patients can pay their bills",
                }
            ),
            403,
        )

    # Ensure JSON data is provided
    data = request.json
    if not data or "amount" not in data or "payment_method" not in data:
        return jsonify({"status": 400, "errors": "Missing required fields"}), 400

    amount = data["amount"]
    payment_method = data["payment_method"]

    conn = db_connection()
    cursor = conn.cursor()
    try:
        # Begin transaction
        conn.autocommit = False

        # Fetch the patient's bill and total amount from either hospitalization or appointment tables
        cursor.execute(
            """
            SELECT b.total_amount, b.status_
            FROM bill_ b
            JOIN (
                SELECT patient_patient_id, bill__bill_id
                FROM hospitalization
                UNION
                SELECT patient_patient_id, bill__bill_id
                FROM appointment
            ) p ON b.bill_id = p.bill__bill_id
            WHERE b.bill_id = %s AND p.patient_patient_id = %s;
        """,
            (bill_id, patient_id),
        )
        bill = cursor.fetchone()

        # If bill does not exist or does not belong to the patient
        if not bill:
            conn.rollback()
            return (
                jsonify(
                    {
                        "status": 404,
                        "errors": "Bill not found or does not belong to the patient",
                    }
                ),
                404,
            )

        total_amount, status_ = bill
        if status_:
            conn.rollback()
            return jsonify({"status": 400, "errors": "This bill is already paid"}), 400

        # Calculate remaining amount
        remaining_value = total_amount - amount

        if remaining_value <= 0:
            cursor.execute(
                """
                UPDATE bill_
                SET status_ = TRUE,
                    total_amount = 0
                WHERE bill_id = %s;
            """,
                (bill_id,),
            )
        else:
            # Update the total_amount in the bill_ table after deducting the payment amount
            cursor.execute(
                """
                UPDATE bill_
                SET total_amount = %s
                WHERE bill_id = %s;
            """,
                (remaining_value, bill_id),
            )

        # Insert payment record with current date
        cursor.execute(
            """
            INSERT INTO payment (bill__bill_id, amount, payment_method, date_payment)
            VALUES (%s, %s, %s, CURRENT_DATE);
        """,
            (bill_id, amount, payment_method),
        )

        # Commit transaction
        conn.commit()
        result = {
            "remaining_value": max(remaining_value, 0)  # To avoid negative values
        }
        return jsonify({"status": 200, "results": result}), 200
    except Exception as e:
        # Rollback on error
        conn.rollback()
        return jsonify({"status": 500, "errors": str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@app.route("/dbproj/top3", methods=["GET"])
@token_required
def get_top_three_patients():
    # Check if the requester is an assistant
    token = request.headers.get("Authorization", "").split(" ")[1]
    user_role, _ = get_user_role_and_id_from_token(token)
    if user_role != "assistant":
        return jsonify({"status": 403, "errors": "Unauthorized access"}), 403

    conn = db_connection()
    if not conn:
        return jsonify({"status": 500, "errors": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
            WITH MonthlyPayments AS (
                SELECT COALESCE(a.patient_patient_id, h.patient_patient_id) AS patient_id, SUM(p.amount) AS total_spent
                FROM Payment p
                LEFT JOIN Bill_ b ON p.bill__bill_id = b.bill_id
                LEFT JOIN Appointment a ON b.bill_id = a.bill__bill_id
                LEFT JOIN Hospitalization h ON b.bill_id = h.bill__bill_id
                WHERE p.date_payment >= date_trunc('month', current_date)
                      AND p.date_payment < date_trunc('month', current_date) + interval '1 month'
                GROUP BY COALESCE(a.patient_patient_id, h.patient_patient_id)
            ),
            ProcedureDetails AS (
                SELECT p.patient_id,
                       json_agg(
                           json_build_object(
                               'type', 'Appointment',
                               'id', a.appointment_id,
                               'doctor_id', a.doctor_specialization_employee_employee_id,
                               'date', a.date_appointment
                           ) ORDER BY a.date_appointment) FILTER (WHERE a.appointment_id IS NOT NULL) AS appointment_details,
                       json_agg(
                           json_build_object(
                               'type', 'Hospitalization',
                               'id', h.hospitalization_id,
                               'nurse_id', h.nurse_employee_employee_id,
                               'admission_date', h.admission_date,
                               'discharge_date', h.discharge_date
                           ) ORDER BY h.admission_date) FILTER (WHERE h.hospitalization_id IS NOT NULL) AS hospitalization_details
                FROM Patient p
                LEFT JOIN Appointment a ON p.patient_id = a.patient_patient_id
                LEFT JOIN Hospitalization h ON p.patient_id = h.patient_patient_id
                GROUP BY p.patient_id
            )
            SELECT p.name AS patient_name, mp.total_spent, pd.appointment_details, pd.hospitalization_details
            FROM MonthlyPayments mp
            JOIN Patient p ON mp.patient_id = p.patient_id
            JOIN ProcedureDetails pd ON mp.patient_id = pd.patient_id
            ORDER BY mp.total_spent DESC
            LIMIT 3
        """
        )
        rows = cursor.fetchall()

        if not rows:
            return jsonify({"status": 404, "errors": "No data found"}), 404

        results = [
            {
                "patient_name": row["patient_name"],
                "amount_spent": row["total_spent"],
                "procedures": {
                    "appointments": row["appointment_details"],
                    "hospitalizations": row["hospitalization_details"],
                },
            }
            for row in rows
        ]

        cursor.close()
        return jsonify({"status": 200, "results": results}), 200

    except Exception as e:
        return jsonify({"status": 500, "errors": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route(
    "/dbproj/daily/<string:year_month_day>", methods=["GET"]
)  # Use 'string' instead of 'date'
@token_required
def get_daily_summary(year_month_day):
    # Check if the requester is an assistant
    token = request.headers.get("Authorization", "").split(" ")[1]
    user_role, _ = get_user_role_and_id_from_token(token)
    if user_role != "assistant":
        return jsonify({"status": 403, "errors": "Unauthorized access"}), 403

    # Convert the year_month_day string to a date object
    try:
        date_object = datetime.strptime(year_month_day, "%Y-%m-%d")
    except ValueError:
        return (
            jsonify(
                {"status": 400, "errors": "Invalid date format, expected YYYY-MM-DD"}
            ),
            400,
        )

    conn = db_connection()
    if not conn:
        return jsonify({"status": 500, "errors": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            """
        SELECT
            SUM(p.amount) AS amount_spent,
            (SELECT COUNT(DISTINCT s.surgery_id)
            FROM Surgery s
            WHERE s.date_surgery = %s) AS surgeries, 
            (SELECT COUNT(DISTINCT pr.prescription_id_)
            FROM Prescription pr
            JOIN appointment_prescription ap ON pr.prescription_id_ = ap.prescription_prescription_id_
            JOIN Appointment a ON ap.appointment_appointment_id = a.appointment_id
            WHERE pr.prescription_date = %s) +
            (SELECT COUNT(DISTINCT pr.prescription_id_)
            FROM Prescription pr
            JOIN hospitalization_prescription hp ON pr.prescription_id_ = hp.prescription_prescription_id_
            JOIN Hospitalization h ON hp.hospitalization_hospitalization_id = h.hospitalization_id
            WHERE pr.prescription_date = %s) AS prescriptions
        FROM Hospitalization h
        LEFT JOIN Payment p ON h.bill__bill_id = p.bill__bill_id AND p.date_payment = %s
        WHERE h.admission_date <= %s AND (h.discharge_date >= %s OR h.discharge_date IS NULL)
    """,
            (
                date_object,
                date_object,
                date_object,
                date_object,
                date_object,
                date_object,
            ),
        )

        result = cursor.fetchone()

        cursor.close()
        if not result:
            return jsonify({"status": 404, "errors": "No data found"}), 404

        return (
            jsonify(
                {
                    "status": 200,
                    "results": {
                        "amount_spent": result["amount_spent"]
                        if result["amount_spent"]
                        else 0,
                        "surgeries": result["surgeries"],
                        "prescriptions": result["prescriptions"],
                    },
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"status": 500, "errors": str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route("/dbproj/report", methods=["GET"])
@token_required
def generate_monthly_report():
    token = request.headers.get("Authorization", "").split(" ")[1]
    user_role, _ = get_user_role_and_id_from_token(token)
    if user_role != "assistant":
        return jsonify({"status": 403, "errors": "Unauthorized access"}), 403

    # Connect to the database
    conn = db_connection()
    cursor = conn.cursor()

    try:
        # SQL query to retrieve the monthly report
        cursor.execute(
            """
            SELECT
                TO_CHAR(surgery.date_surgery, 'YYYY-MM') AS month,
                employee.name AS doctor,
                COUNT(*) AS surgeries
            FROM
                surgery
            JOIN
                doctor_specialization ON surgery.doctor_specialization_employee_employee_id = doctor_specialization.employee_employee_id
            JOIN
                employee ON doctor_specialization.employee_employee_id = employee.employee_id
            WHERE
                surgery.date_surgery >= CURRENT_DATE - INTERVAL '1 year' AND
                surgery.date_surgery <= CURRENT_DATE -- Get surgeries within the last year but not after the current date
            GROUP BY
                TO_CHAR(surgery.date_surgery, 'YYYY-MM'),
                employee.name
            ORDER BY
                TO_CHAR(surgery.date_surgery, 'YYYY-MM') DESC,
                surgeries DESC
            LIMIT
                12;
        """
        )

        rows = cursor.fetchall()

        # Dictionary to store the doctor with the most surgeries for each month
        report_dict = {}

        # Iterate over query results to populate report_dict
        for row in rows:
            month = row[0]
            doctor = row[1]
            surgeries = row[2]

            # Check if the month already exists in report_dict
            if month not in report_dict:
                # If not, add the doctor as the doctor with the most surgeries for that month
                report_dict[month] = {"doctor": doctor, "surgeries": surgeries}
            else:
                # If yes, compare the surgeries with the current maximum surgeries for that month
                # If the current doctor has more surgeries, update the entry in report_dict
                if surgeries > report_dict[month]["surgeries"]:
                    report_dict[month] = {"doctor": doctor, "surgeries": surgeries}

        # Convert report_dict to the desired JSON format
        report = [
            {"month": month, "doctor": entry["doctor"], "surgeries": entry["surgeries"]}
            for month, entry in report_dict.items()
        ]

        # Return the JSON response
        return (
            jsonify({"status": StatusCodes["success"], "results": report}),
            StatusCodes["success"],
        )
    except Exception as e:

        return (
            jsonify({"status": StatusCodes["internal_error"], "errors": str(e)}),
            StatusCodes["internal_error"],
        )
    finally:

        cursor.close()
        conn.close()


if __name__ == "__main__":

    # set up logging
    logging.basicConfig(filename="log_file.log")
    logger = logging.getLogger("logger")
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s]:  %(message)s", "%H:%M:%S"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    host = "127.0.0.1"
    port = 8080
    app.run(host=host, debug=True, threaded=True, port=port)
    logger.info(f"API v1.0 online: http://{host}:{port}")
