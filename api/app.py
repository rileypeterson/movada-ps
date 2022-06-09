from flask import Flask, render_template, request, redirect, url_for, flash, session
import validators
import subprocess
from constants import ROOT_DIR
import os
import traceback
import zmq
import json


app = Flask(__name__)
app.secret_key = b"qe9r 8g3408he9uhwe9d8"
first_visit = True


@app.route("/", methods=["GET", "POST"])
def movada():
    global first_visit
    if first_visit:
        session.clear()
        first_visit = False
    message = ""
    if request.method == "GET":
        data = session.get("data", None)
        print(data)
        if data:
            context = zmq.Context()
            socket = context.socket(zmq.SUB)
            port = data["port"]
            url = data["url"]
            socket.connect(f"tcp://localhost:{port}")
            flash("SOCKET START on " + f"tcp://localhost:{port}")
            # root = "https://www.bovada.lv/sports/baseball/"
            topics = [""]
            flash(f"SUBSCRIBING to {url}")
            for topic in topics:
                socket.subscribe(url + topic)
            url, data = socket.recv_multipart()
            flash(f"RECEIVED: {url.decode() + data.decode()}")
        return render_template("index.html")
    else:
        if "url" in request.form and "port" in request.form:
            url = request.form.get("url")
            if validators.url(url):
                try:
                    port = int(request.form.get("port"))
                except ValueError:
                    message = f"Invalid Port Number: {request.form.get('port')}"
                    return render_template("index.html", result=message)
                try:
                    subprocess.Popen(
                        [
                            "python",
                            os.path.join(
                                ROOT_DIR, "movada-ps/movada_ps/spiders/movada_pub.py"
                            ),
                            "--port",
                            f"{port}",
                            "--url",
                            f"{url}",
                        ]
                    )
                    flash(f"Started stream on {port} for {url}")
                    session["data"] = dict(port=port, url=url)
                    return redirect(url_for("movada"))
                except Exception as e:
                    traceback.print_exc()
            else:
                message = "Not a valid URL"
        else:
            message = "Incomplete Form Data Submitted"

        return render_template("index.html", result=message)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port="5555", debug=True)
