source venv/bin/activate
export $(cat .env | xargs)
python main.py