@echo off
echo Starting AgroNex Servers...

start cmd /k "cd backend && (if exist venv\Scripts\activate call venv\Scripts\activate) && python -m uvicorn main:app --port 8000 --reload"
start cmd /k "cd frontend && npm run dev"


echo Both servers have been launched in separate windows!