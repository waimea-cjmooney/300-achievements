#===========================================================
# Logging Middleware
#===========================================================

from flask import request, session
from dotenv import load_dotenv
from os import getenv
from colorama import Fore, init
from datetime import datetime
import logging

# Colorama config
init(autoreset=True)

# Logging colours
REQUEST_COL = Fore.CYAN
ROUTE_COL   = Fore.BLUE
SESSION_COL = Fore.YELLOW
DB_COL      = Fore.MAGENTA


# Load Flask and Turso environment variables from the .env file
load_dotenv()
HOST = getenv("FLASK_RUN_HOST", "localhost")
PORT = getenv("FLASK_RUN_PORT", 5000)

# Disable built-in logging
logging.getLogger('werkzeug').setLevel(logging.CRITICAL)


#-----------------------------------------------------------
# Return a coloured status message
#-----------------------------------------------------------
def colStatus(response):
    if response.status_code < 300:
        return f"{Fore.GREEN}{response.status}"
    if response.status_code < 400:
        return f"{Fore.YELLOW}{response.status}"
    return f"{Fore.RED}{response.status}"


#-----------------------------------------------------------
# Provide logging handlers to the Flask app
#-----------------------------------------------------------
def init_logging(app):
    # Announce the app...
    print(f"\n🚀 Flask server is running at {Fore.GREEN}http://{HOST}:{PORT}\n")


    #--------------------------------------------------
    # Pre-request logging
    #--------------------------------------------------
    @app.before_request
    def log_request():
        # Don't log at start for static files
        if app.debug and not '/static/' in request.path:
            now = datetime.now().strftime("%H:%M:%S")

            # The URL
            print(f"[{now}] Request: {REQUEST_COL}{request.method} {request.path}")
            # Matched routing rule
            if request.url_rule:
                print(f"           Matches: {ROUTE_COL}{request.method.lower()}(\"{request.url_rule}\")")
            # Matched route function name
            if request.endpoint:
                print(f"           Handler: {ROUTE_COL}{request.endpoint}()")
            # URL params, if any
            if request.view_args:
                print(f"            Params: {ROUTE_COL}{request.view_args}")
            # Any GET args
            if request.args:
                print(f"              Args: {ROUTE_COL}{dict(request.args)}")
            # Any form data
            if request.form:
                print(f"              Form: {ROUTE_COL}{dict(request.form)}")
            # Any files uploaded
            if request.files:
                print(f"             Files: {ROUTE_COL}{dict(request.files)}")
            # Any session values
            if session:
                print(f"           Session: {SESSION_COL}{dict(session)}")


    #--------------------------------------------------
    # Post-request logging
    #--------------------------------------------------
    @app.after_request
    def log_response(response):
        if app.debug:
            # Was this a matched route?
            if not '/static/' in request.path:
                # Yes, so complete it
                print(f"            Status: {colStatus(response)}{Fore.RESET}\n")
            else:
                # Nope, a static file, so show the full request/response
                now = datetime.now().strftime("%H:%M:%S")
                print(f"[{now}] Request: {REQUEST_COL}{request.method} {request.path} {colStatus(response)}{Fore.RESET}\n")

            return response


#-----------------------------------------------------------
# Converts the row data from a DB result set into a well
# formatted string, not including large BLOB data, instead
# adding a summary of the data
#-----------------------------------------------------------
def _format_result_rows(result):
    spacing = " " * 20
    columns = result.columns

    summarised = "[\n"
    for row in result.rows:
        row_summary = f"{spacing}  {{\n"
        for col, val in zip(columns, row):
            row_summary += f"{spacing}    {col}: "
            row_summary += f"<BLOB {len(val)} bytes>" if isinstance(val, (bytes, bytearray)) else f"'{val}'"
            row_summary += ",\n"
        row_summary += f"{spacing}  }},\n"
        summarised += row_summary
    summarised += f"{spacing}]"

    return summarised


#-----------------------------------------------------------
# Log a given SQL request - Call prior to running the SQL
#-----------------------------------------------------------
def log_db_request(app, sql, params):
    if app.debug:
        print(f"            DB SQL: {DB_COL}{sql}")
        print(f"            Params: {DB_COL}{params[0] if params else 'None'}")


#-----------------------------------------------------------
# Log result of an SQL request - Call after running the SQL
#-----------------------------------------------------------
def log_db_result(app, sql, result):
    if app.debug:
        sqlUp = sql.upper()

        if 'SELECT' in sqlUp:
            print(f"          Row Data: {DB_COL}{_format_result_rows(result)}")

        elif 'UPDATE' in sqlUp or 'DELETE' in sqlUp:
            print(f"              Rows: {DB_COL}{getattr(result, 'rows_affected', result)}")

        elif 'INSERT' in sqlUp:
            print(f"            New ID: {DB_COL}{getattr(result, 'last_insert_rowid', result)}")

