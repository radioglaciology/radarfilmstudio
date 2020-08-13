import os

from explore_app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=os.environ.get('PORT'))