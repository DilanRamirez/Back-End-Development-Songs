from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route("/health")
def health():
    return jsonify(dict(status="OK")), 200


@app.route("/count")
def count():
    """Return the length of data"""
    if songs_list is not None:
        return jsonify(length=len(songs_list)), 200
    return jsonify(message="Internal server error"), 500


@app.route("/song", methods=["GET"])
def songs():
    # Retrieve all song documents from the MongoDB collection
    cursor = db.songs.find({})
    songs_data = list(cursor)
    # Convert the BSON documents to JSON serializable Python objects
    songs_json = parse_json(songs_data)
    return jsonify({"songs": songs_json}), 200

@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    # Find the song document with the matching "id"
    song = db.songs.find_one({"id": id})
    if song is None:
        return jsonify({"message": "song with id not found"}), 404
    # Convert the BSON document to a JSON-serializable Python dict
    return jsonify(parse_json(song)), 200

@app.route("/song", methods=["POST"])
def create_song():
    # Ensure the request contains JSON data
    if not request.json:
        abort(400, description="Request body must be JSON")
    
    new_song = request.get_json()
    
    # Check if a song with the provided id already exists
    if db.songs.find_one({"id": new_song.get("id")}):
        return jsonify({"Message": f"song with id {new_song.get('id')} already present"}), 302

    # Insert the new song into the MongoDB collection
    result: InsertOneResult = db.songs.insert_one(new_song)
    
    # Return the inserted id in a JSON response
    return parse_json({"inserted id": result.inserted_id}), 201

@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    # Ensure the request contains JSON data
    if not request.json:
        abort(400, description="Request body must be JSON")
    
    update_data = request.get_json()
    
    # Find the song in the database by id
    song = db.songs.find_one({"id": id})
    if song is None:
        return jsonify({"message": "song not found"}), 404
    
    # Attempt to update the song with the new data
    result = db.songs.update_one({"id": id}, {"$set": update_data})
    
    if result.modified_count > 0:
        # If the update changed anything, fetch and return the updated document with a 201 status
        updated_song = db.songs.find_one({"id": id})
        return jsonify(parse_json(updated_song)), 201
    else:
        # No fields were changed, return a 200 with an appropriate message
        return jsonify({"message": "song found, but nothing updated"}), 200

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    # Attempt to delete the song with the given id
    result = db.songs.delete_one({"id": id})
    
    if result.deleted_count == 0:
        return jsonify({"message": "song not found"}), 404
    
    # If deletion is successful, return an empty body with a 204 status
    return "", 204
