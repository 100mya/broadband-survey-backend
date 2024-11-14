from flask import Flask, request, jsonify
from flask_cors import CORS
import pymongo
from pymongo import MongoClient
import os
from dotenv import load_dotenv  # Ensure you have python-dotenv installed
import subprocess
import json

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# MongoDB Atlas connection string from environment variable
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://soumya15pandey:D6E1eEyNFmTxlvCW@cluster0.ezdiv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

# Initialize MongoDB client and verify connection
try:
    client = MongoClient(MONGODB_URI)
    # Check if the connection is established by pinging the server
    client.admin.command('ping')  # This will raise an exception if not connected
    db = client['broadbandSurvey']
    collection = db['surveyResponses']
    app.logger.info("Successfully connected to MongoDB.")
except Exception as e:
    app.logger.error(f"Failed to connect to MongoDB: {str(e)}")
    # Optionally, you can exit the application if the connection fails
    exit(1)

# Route to run the speed test
@app.route('/api/run_speedtest', methods=['GET'])
def run_speedtest():
    try:
        # Run the speedtest command and capture both stdout and stderr
        result = subprocess.run(['speedtest', '-f', 'json'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Log the stderr output to help with debugging
        if result.stderr:
            app.logger.error(f"Speedtest stderr: {result.stderr.decode('utf-8')}")

        # Check if the command failed
        if result.returncode != 0:
            raise Exception(f"Speedtest failed with return code {result.returncode}")

        # Parse the stdout to JSON
        speedtest_data = json.loads(result.stdout)

        # Extract download, upload bandwidth, and ISP
        download_speed_Bps = speedtest_data['download']['bandwidth']  # Bytes per second
        upload_speed_Bps = speedtest_data['upload']['bandwidth']      # Bytes per second

        # Convert from Bytes per second (Bps) to Megabits per second (Mbps)
        download_speed_mbps = (download_speed_Bps * 8) / 1e6  # Convert from Bps to Mbps
        upload_speed_mbps = (upload_speed_Bps * 8) / 1e6      # Convert from Bps to Mbps

        # Extract ISP name
        isp = speedtest_data['isp']

        # Return results as JSON
        return jsonify({
            'downloadSpeed': f"{download_speed_mbps:.2f}",
            'uploadSpeed': f"{upload_speed_mbps:.2f}",
            'isp': isp
        }), 200

    except json.JSONDecodeError:
        app.logger.error("Failed to parse speedtest output as JSON.")
        return jsonify({"message": "Failed to parse speedtest output as JSON."}), 500

    except Exception as e:
        app.logger.error(f"Failed to run speedtest: {str(e)}")
        return jsonify({"message": "Error running speedtest", "error": str(e)}), 500



# Route to handle survey data submission
@app.route('/api/survey', methods=['POST'])
def submit_survey():
    data = request.get_json()
    app.logger.debug(f"Received data: {data}")  # Log incoming data

    # Validate required fields
    required_fields = ['street', 'city', 'county', 'zipCode', 'hasInternet', 'isp', 'downloadSpeed', 'uploadSpeed', 'deviceType']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({"message": f"Field {field} is required"}), 400

    # Insert the data into MongoDB
    try:
        collection.insert_one(data)
        return jsonify({"message": "Survey submitted successfully"}), 200
    except Exception as e:
        return jsonify({"message": "Error saving data", "error": str(e)}), 500

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
