from flask import Flask, render_template, Response, jsonify, request
import cv2
from cvzone.HandTrackingModule import HandDetector
from cvzone.ClassificationModule import Classifier
import numpy as np
import math
from collections import Counter

app = Flask(__name__)

cap = cv2.VideoCapture(0)
detector = HandDetector(maxHands=1)
classifier = Classifier("Model/keras_model.h5", "Model/labels.txt")

offset = 20
imgSize = 300
labels = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
    "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "space"
]

# State variables
prediction_history = []
history_length = 8        # tighter smoothing
confidence_threshold = 0.9
stability_ratio = 0.75
gap_threshold = 0.2       # ensures winner is clearly stronger

stable_letter = "??"
sentence = ""
latest_confidence = 0.0
latest_stability = 0.0

# Flag to prevent spamming same letter
letter_locked = False


def generate_frames():
    global stable_letter, sentence
    global latest_confidence, latest_stability
    global letter_locked

    while True:
        success, img = cap.read()
        if not success:
            break

        imgOutput = img.copy()
        hands, img = detector.findHands(img)

        if hands:
            hand = hands[0]
            x, y, w, h = hand['bbox']
            imgWhite = np.ones((imgSize, imgSize, 3), np.uint8) * 255

            height, width, _ = img.shape
            x1 = max(0, x - offset)
            y1 = max(0, y - offset)
            x2 = min(width, x + w + offset)
            y2 = min(height, y + h + offset)
            imgCrop = img[y1:y2, x1:x2]

            if imgCrop.size != 0:
                aspectRatio = h / w
                if aspectRatio > 1:
                    k = imgSize / h
                    wCal = math.ceil(k * w)
                    imgResize = cv2.resize(imgCrop, (wCal, imgSize))
                    wGap = math.ceil((imgSize - wCal) / 2)
                    imgWhite[:, wGap:wCal + wGap] = imgResize
                else:
                    k = imgSize / w
                    hCal = math.ceil(k * h)
                    imgResize = cv2.resize(imgCrop, (imgSize, hCal))
                    hGap = math.ceil((imgSize - hCal) / 2)
                    imgWhite[hGap:hCal + hGap, :] = imgResize

                prediction, index = classifier.getPrediction(imgWhite, draw=False)

                # Add prediction to history
                prediction_history.append(index)
                if len(prediction_history) > history_length:
                    prediction_history.pop(0)

                # Count frequency of predictions
                counts = Counter(prediction_history)
                most_common = counts.most_common(2)

                most_common_index, count = most_common[0]
                latest_confidence = float(prediction[most_common_index])
                latest_stability = count / len(prediction_history)

                # Gap filter: check runner-up difference
                if len(most_common) > 1:
                    second_count = most_common[1][1]
                    gap = (count - second_count) / len(prediction_history)
                else:
                    gap = 1.0  # only one candidate

                if (most_common_index < len(labels)
                    and latest_confidence > confidence_threshold
                    and latest_stability > stability_ratio
                    and gap > gap_threshold):

                    stable_letter = labels[most_common_index]

                    # Only add letter if not locked
                    if not letter_locked and stable_letter != "??":
                        if stable_letter == "space":
                            sentence += " "
                        else:
                            sentence += stable_letter
                        letter_locked = True  # lock until hand is removed
                else:
                    stable_letter = "??"

                cv2.rectangle(imgOutput, (x - offset, y - offset),
                              (x + w + offset, y + h + offset), (255, 0, 255), 4)

        else:
            # No hand detected → unlock the letter
            letter_locked = False

        ret, buffer = cv2.imencode('.jpg', imgOutput)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video')
def video():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/get_sentence')
def get_sentence():
    return jsonify({
        "sentence": sentence,
        "letter": stable_letter,
        "confidence": latest_confidence,
        "stability": latest_stability
    })


@app.route('/clear_sentence', methods=['POST'])
def clear_sentence():
    global sentence
    sentence = ""
    return ("", 204)


@app.route('/backspace', methods=['POST'])
def backspace():
    global sentence
    sentence = sentence[:-1]
    return ("", 204)


@app.route('/commit_space', methods=['POST'])
def commit_space():
    global sentence
    sentence += " "
    return ("", 204)


if __name__ == "__main__":
    app.run(debug=True)
