import functions_framework
import json
from google.auth import default
from googleapiclient.discovery import build
from google.cloud import storage
import os

@functions_framework.http
def get_last_movie_watched(request):
    """
        Returns the last movie watched.
        Data is read from MyMoviesDb Google Sheet
        values:
            title: Movie Title
            rating: My Movie Rating from 1 to 10
            comment: My personal short comment about the movie
            imdb_link: Link to the IMDB movie page
            poster_link: Link to the poster image
    """
    SPREADSHEET_ID = "1evnjLFzM3apXph0sUahqcbCwuEKCeAZh6bp3bdshSm4"
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    BUCKET_NAME = os.environ.get("BUCKET_NAME")
    print(BUCKET_NAME)
    FILE_NAME = 'last_movie_watched.json'

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
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range="LastMovieWatched!A2:E2").execute()
    values = result.get("values", [])[0]

    output = {}
    output['title'] = values[0]
    output['rating'] = values[1]
    output['comment'] = values[2]
    output['imdb_link'] = values[3]
    output['poster_link'] = values[4]
    
    save_to_gcs(BUCKET_NAME, FILE_NAME, output)
    return (json.dumps(output), 200, headers)


def save_to_gcs(bucket_name, file_name, data):
    client = storage.Client() 
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)

    blob.upload_from_string(json.dumps(data), content_type='application/json')