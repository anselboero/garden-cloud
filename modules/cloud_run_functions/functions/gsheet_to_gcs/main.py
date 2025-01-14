import functions_framework
import json
from google.auth import default
from googleapiclient.discovery import build
from google.cloud import storage
import os

@functions_framework.http
def gsheet_to_gcs(request):
    """
        Given a spreadsheet containing a Sheet called API,
        a GCS bucket name and the output json name,
        will read the given sheet and store the output as a JSON
        into the specified bucket.
        needed data:
            # Variables
            spreadsheet_id = "your_spreadsheet_id"   # The ID of the spreadsheet
            gcs_bucket_name = "your_bucket_name"     # The name of the Google Cloud Storage bucket
            json_output_filename = "output.json"     # The desired name for the JSON output file
    """
    
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    data = request.get_json()
    spreadsheet_id = data['spreadsheet_id']
    gcs_bucket_name = data['gcs_bucket_name']
    json_output_filename = data['json_output_filename']
    sheet_name = 'API'

    credentials, _ = default(scopes = SCOPES)
    service = build("sheets", "v4", credentials=credentials)

    sheet = service.spreadsheets()

    # Reading LastMovieWatched sheet, first row only
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range="API!A:B").execute()
    values = result.get("values", [])

    output = {}
    for row in values:
        ## check if the key is non-empty
        if row[0]:
            output[row[0]] = row[1] if len(row) > 1 else None
    
    
    
    save_to_gcs(gcs_bucket_name, json_output_filename, output)
    
    #save_to_gcs(BUCKET_NAME, FILE_NAME, output)
    return (json.dumps(output), 200)

    return data

def save_to_gcs(gcs_bucket_name, file_name, data):
    client = storage.Client() 
    bucket = client.bucket(gcs_bucket_name)
    blob = bucket.blob(file_name)

    blob.upload_from_string(json.dumps(data), content_type='application/json')