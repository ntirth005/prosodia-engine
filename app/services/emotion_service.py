from transformers import pipeline
from typing import List, Dict

emotion_classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    top_k=None  # replaces return_all_scores
)


def classify_phrase_emotion(phrase: str) -> Dict:

    results = emotion_classifier(phrase)[0]

    # Convert list of predictions into dictionary
    scores = {item["label"].lower(): item["score"] for item in results}

    emotion = max(scores, key=scores.get)
    confidence = scores[emotion]

    return {
        "phrase": phrase,
        "emotion": emotion,
        "confidence": round(confidence, 4),
        "distribution": scores
    }


def classify_emotions(phrases: List[str]) -> List[Dict]:

    outputs = []

    for phrase in phrases:
        outputs.append(classify_phrase_emotion(phrase))

    return outputs