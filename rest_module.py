#!/usr/bin/env python
import os

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)


@app.route("/")
def main_form():
    return render_template("main_form.html")


@app.route("/", methods=["POST"])
def proccess_request():
    text = request.form["text"]
    result = brain.get_answer(text)
    return result


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
