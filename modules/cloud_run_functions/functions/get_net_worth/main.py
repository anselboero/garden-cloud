import functions_framework
import json
from google.auth import default
from googleapiclient.discovery import build
from google.cloud import storage
import os

@functions_framework.http
def get_net_worth(request):
    """
        TODO
    """
    SPREADSHEET_ID = "1G_CqV95lI7r-XtgpO5UOzsB_h77G4JVV9kThdzfsujk"
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    BUCKET_NAME = os.environ.get("BUCKET_NAME")
    print(BUCKET_NAME)
    FILE_NAME = 'net_worth.json'

    headers = {
        'ContentType': 'application/json',
        'Access-Control-Allow-Origin': 'https://anselboero.com',
        'Access-Control-Allow-Methods': 'GET',
        'Access-Control-Allow-Headers': 'Content-Type',
    }
    
    credentials, _ = default(scopes = SCOPES)
    service = build("sheets", "v4", credentials=credentials)

    sheet = service.spreadsheets()

    # Reading LastMovieWatched sheet, first row only
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="API!A:B").execute()
    values = result.get("values", [])

    output = {}
    for row in values:
        output[row[0]] = row[1]
    
    
    
    save_to_gcs(BUCKET_NAME, FILE_NAME, output)
    
    #save_to_gcs(BUCKET_NAME, FILE_NAME, output)
    return (json.dumps(output), 200, headers)


def save_to_gcs(bucket_name, file_name, data):
    client = storage.Client() 
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)

    blob.upload_from_string(json.dumps(data), content_type='application/json')