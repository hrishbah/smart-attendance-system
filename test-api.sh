#!/bin/bash
# API smoke tests - run after docker compose up -d and start-backend.sh
set -e
BASE="http://localhost:8000/api"
COOKIE_JAR="/tmp/attendance_test_cookies.txt"

echo "=== API Smoke Tests ==="

# Health
curl -sf "$BASE/health" | grep -q ok && echo "✓ Health check"

# Admin login
curl -sf -c "$COOKIE_JAR" -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@attendance.edu","password":"admin123"}' > /tmp/login.json
grep -q admin /tmp/login.json && echo "✓ Admin login"

# Find Hrishabh
curl -sf -b "$COOKIE_JAR" "$BASE/students?search=Hrishabh" > /tmp/students.json
grep -q "2500971520093" /tmp/students.json && echo "✓ Hrishabh Bajpai in database"
grep -q "not_registered" /tmp/students.json && echo "✓ Face status: NOT REGISTERED (expected before webcam registration)"

# Subjects
curl -sf -b "$COOKIE_JAR" "$BASE/subjects" > /tmp/subjects.json
grep -q "Mathematics 2" /tmp/subjects.json && echo "✓ Mathematics 2 subject exists"

# Faculty login
curl -sf -c /tmp/faculty_cookies.txt -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"rajesh.kumar@college.edu","password":"faculty123"}' > /tmp/faculty_login.json
grep -q faculty /tmp/faculty_login.json && echo "✓ Faculty login"

# Dashboard stats (real DB)
curl -sf -b "$COOKIE_JAR" "$BASE/dashboard/stats" > /tmp/stats.json
grep -q total_students /tmp/stats.json && echo "✓ Dashboard stats from database"

echo ""
echo "All API smoke tests passed."
echo "Next: test webcam face registration in browser at http://localhost:5173"
