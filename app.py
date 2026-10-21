"""Hugging Face Spaces entrypoint — `python app.py` or Spaces runtime."""

from changeradar.ui import build_app, get_index

get_index()
demo = build_app()

if __name__ == "__main__":
    demo.launch()
