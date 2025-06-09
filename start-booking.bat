@echo off
cd /d "%~dp0booking-service"
set DATABASE_URL=postgresql://postgres:postgres@localhost:5432/booking_db
set JWT_SECRET=your-super-secret-jwt-key
set AUTH_SERVICE_URL=http://localhost:4001
npm run dev 