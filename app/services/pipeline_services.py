import json
from pathlib import Path

try:
	from app.services.phrase_splitter import split_into_phrases
	from app.services.emotion_service import classify_emotions
	from app.services.focus_word_detector import detect_focus_for_phrases
except ModuleNotFoundError:
	import os
	import sys

	project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
	if project_root not in sys.path:
		sys.path.insert(0, project_root)

	from app.services.phrase_splitter import split_into_phrases
	from app.services.emotion_service import classify_emotions
	from app.services.focus_word_detector import detect_focus_for_phrases


def save_emotion_results(emotion_results: list, filename: str = "emotion_results.json") -> Path:
    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / "audio_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(emotion_results, file, indent=2)

    return output_path


def run_demo() -> None:
	text = "I am really sorry for the delay, but we will fix this immediately."
	phrases = split_into_phrases(text)
	emotion_results = classify_emotions(phrases)
	print(emotion_results)
	output_path = save_emotion_results(emotion_results)
	print(f"Saved emotion results to: {output_path}")

	results = detect_focus_for_phrases(phrases)
	print(results)


if __name__ == "__main__":
    run_demo()