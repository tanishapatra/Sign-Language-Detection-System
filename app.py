from flask import Flask, render_template, jsonify, request
import cv2
from cvzone.HandTrackingModule import HandDetector
from cvzone.ClassificationModule import Classifier
import numpy as np
import math
from collections import Counter
import base64

app = Flask(__name__)

# Initialize hand detector & classifier
detector = HandDetector(maxHands=1)
classifier = Classifier("Model/keras_model.h5", "Model/labels.txt")

# Parameters
OFFSET = 20
IMG_SIZE = 300
LABELS = [*list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "space"]
HISTORY_LENGTH = 8
CONF_THRESHOLD = 0.9
STABILITY_RATIO = 0.75
GAP_THRESHOLD = 0.2

# State
prediction_history = []
stable_letter = "??"
sentence = ""
latest_confidence = 0.0
latest_stability = 0.0
letter_locked = False

def process_frame(img):
    global stable_letter, sentence, latest_confidence, latest_stability, letter_locked

    hands, _ = detector.findHands(img)
    if hands:
        hand = hands[0]
        x, y, w, h = hand['bbox']

        # Crop and resize for classification
        imgWhite = np.ones((IMG_SIZE, IMG_SIZE, 3), np.uint8) * 255
        height, width, _ = img.shape
        x1, y1 = max(0, x - OFFSET), max(0, y - OFFSET)
        x2, y2 = min(width, x + w + OFFSET), min(height, y + h + OFFSET)
        imgCrop = img[y1:y2, x1:x2]

        if imgCrop.size != 0:
            aspectRatio = h / w
            if aspectRatio > 1:
                k = IMG_SIZE / h
                wCal = math.ceil(k * w)
                imgResize = cv2.resize(imgCrop, (wCal, IMG_SIZE))
                wGap = math.ceil((IMG_SIZE - wCal) / 2)
                imgWhite[:, wGap:wCal + wGap] = imgResize
            else:
                k = IMG_SIZE / w
                hCal = math.ceil(k * h)
                imgResize = cv2.resize(imgCrop, (IMG_SIZE, hCal))
                hGap = math.ceil((IMG_SIZE - hCal) / 2)
                imgWhite[hGap:hCal + hGap, :] = imgResize

            prediction, index = classifier.getPrediction(imgWhite, draw=False)

            # Update prediction history
            prediction_history.append(index)
            if len(prediction_history) > HISTORY_LENGTH:
                prediction_history.pop(0)

            counts = Counter(prediction_history)
            most_common = counts.most_common(2)
            most_common_index, count = most_common[0]

            latest_confidence = float(prediction[most_common_index])
            latest_stability = count / len(prediction_history)
            second_count = most_common[1][1] if len(most_common) > 1 else 0
            gap = (count - second_count) / len(prediction_history)

            if latest_confidence > CONF_THRESHOLD and latest_stability > STABILITY_RATIO and gap > GAP_THRESHOLD:
                stable_letter = LABELS[most_common_index]
                if not letter_locked and stable_letter != "??":
                    sentence += " " if stable_letter == "space" else stable_letter
                    letter_locked = True
            else:
                stable_letter = "??"
    else:
        letter_locked = False
        stable_letter = "??"

    return img

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    global sentence
    try:
        data = request.json
        img_data = data['image']
        img_bytes = base64.b64decode(img_data.split(',')[1])
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        process_frame(img)

        return jsonify({
            "letter": stable_letter,
            "sentence": sentence,
            "confidence": latest_confidence,
            "stability": latest_stability
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/clear_sentence', methods=['POST'])
def clear_sentence():
    global sentence
    sentence = ""
    return "", 204

@app.route('/backspace', methods=['POST'])
def backspace():
    global sentence
    sentence = sentence[:-1]
    return "", 204

@app.route('/commit_space', methods=['POST'])
def commit_space():
    global sentence
    sentence += " "
    return "", 204

if __name__ == "__main__":
    app.run(debug=True)
