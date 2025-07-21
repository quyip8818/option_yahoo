python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt
pip install --upgrade websockets

git add . && git commit -m 'fix' && git push
