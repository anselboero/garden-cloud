import functions_framework
import json
from google.auth import default
from googleapiclient.discovery import build

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
    
    return json.dumps(output), 200, {'ContentType': 'application/json'}