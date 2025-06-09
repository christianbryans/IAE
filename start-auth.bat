@echo off
cd /d "%~dp0auth-service"
set DATABASE_URL=postgresql://postgres:postgres@localhost:5432/auth_db
set JWT_SECRET=your-super-secret-jwt-key
npm run dev 