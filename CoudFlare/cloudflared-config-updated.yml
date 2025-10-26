tunnel: thor
credentials-file: C:\ProgramData\cloudflared\556698d2-2814-415f-a31e-4c3c49c1e120.json

ingress:
  # Route /admin and /api to Django backend (port 8000)
  - hostname: thor.360edu.org
    path: /admin/*
    service: http://localhost:8000
  - hostname: thor.360edu.org
    path: /admin
    service: http://localhost:8000
  - hostname: thor.360edu.org
    path: /api/*
    service: http://localhost:8000
  - hostname: thor.360edu.org
    path: /static/*
    service: http://localhost:8000
  - hostname: thor.360edu.org
    path: /media/*
    service: http://localhost:8000
  
  # Route everything else to React frontend (port 5173)
  - hostname: thor.360edu.org
    service: http://localhost:5173
  
  # Catch-all 404
  - service: http_status:404
