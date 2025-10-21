
from flask import Flask, request


app = Flask(__name__)

@app.route('/callback')
def oauth2_callback():
    state = request.args.get('state')
    code = request.args.get('code')

    print(code)
    print(state)

    return "Callback received. You can close this window."


def run_flask_app():
    app.run(port=8080, debug=True)


if __name__ == "__main__":
    run_flask_app()