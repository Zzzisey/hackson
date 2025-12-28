cd e:\project\hackson\backend
python -m app.main

或者

cd e:\project\hackson\backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

使用python内置服务器启动前端：
cd e:\project\hackson\frontend
python -m http.server 3000