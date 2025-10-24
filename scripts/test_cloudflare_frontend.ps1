# Test Cloudflare Frontend Routing
# This script tests all the key URLs to help diagnose the blank page issue

Write-Host "`n🔍 Testing Cloudflare Frontend..." -ForegroundColor Cyan
Write-Host "====================================`n" -ForegroundColor Cyan

# Test 1: Root URL
Write-Host "1. Testing root URL (/):" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "https://thor.360edu.org/" -MaximumRedirection 0 -ErrorAction Stop -UseBasicParsing
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "   No redirect" -ForegroundColor Gray
} catch {
    if ($_.Exception.Response.StatusCode.value__ -in 301,302,303,307,308) {
        $location = $_.Exception.Response.Headers['Location']
        Write-Host "   Status: $($_.Exception.Response.StatusCode.value__) (Redirect)" -ForegroundColor Cyan
        Write-Host "   Location: $location" -ForegroundColor White
    } else {
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Test 2: Login page
Write-Host "`n2. Testing login page (/auth/login):" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "https://thor.360edu.org/auth/login" -UseBasicParsing -TimeoutSec 5
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "   Content-Length: $($response.Content.Length) bytes" -ForegroundColor Cyan
    if ($response.Content -match "<title>(.*?)</title>") {
        Write-Host "   Page Title: $($matches[1])" -ForegroundColor White
    }
} catch {
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Check if main.tsx loads
Write-Host "`n3. Testing main.tsx:" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "https://thor.360edu.org/src/main.tsx" -UseBasicParsing -TimeoutSec 5
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "   Size: $($response.Content.Length) bytes" -ForegroundColor Cyan
} catch {
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Check API
Write-Host "`n4. Testing API (/api/):" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "https://thor.360edu.org/api/" -UseBasicParsing -TimeoutSec 5
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor Green
    if ($response.Content -match "Thor API") {
        Write-Host "   ✅ API responding correctly" -ForegroundColor Green
    }
} catch {
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Check Admin
Write-Host "`n5. Testing Admin (/admin/):" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "https://thor.360edu.org/admin/" -UseBasicParsing -TimeoutSec 5
    Write-Host "   Status: $($response.StatusCode)" -ForegroundColor Green
    if ($response.Content -match "Django") {
        Write-Host "   ✅ Django admin responding" -ForegroundColor Green
    }
} catch {
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n====================================`n" -ForegroundColor Cyan
Write-Host "💡 If root URL shows a redirect to /app/home or /auth/login, that's normal." -ForegroundColor Yellow
Write-Host "💡 The blank page might be:" -ForegroundColor Yellow
Write-Host "   - JavaScript console errors (check browser DevTools F12)" -ForegroundColor Gray
Write-Host "   - API calls failing during app initialization" -ForegroundColor Gray
Write-Host "   - CSS not loading (check Network tab)" -ForegroundColor Gray
Write-Host "`n🌐 Open https://thor.360edu.org/ and press F12 to see console errors`n" -ForegroundColor Cyan
