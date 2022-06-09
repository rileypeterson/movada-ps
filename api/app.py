from flask import Flask, render_template, request, redirect, url_for
import validators
import subprocess
from constants import ROOT_DIR
import os
import traceback

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def movada():
    mesg = ""
    if request.method == "GET":
        return render_template("index.html")
    else:
        if "url" in request.form and "port" in request.form:
            url = request.form.get("url")
            if validators.url(url):
                try:
                    port = int(request.form.get("port"))
                except ValueError:
                    mesg = f"Invalid Port Number: {request.form.get('port')}"
                    return render_template("index.html", result=mesg)
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
                    return redirect(url_for("movada"))
                except Exception as e:
                    traceback.print_exc()
            else:
                mesg = "Not a valid URL"
        else:
            mesg = "Incomplete Form Data Submitted"

        return render_template("index.html", result=mesg)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port="5555", debug=True)
