@echo off
rem ------------------------------------------------------------------
rem Variaveis de ambiente do Caderno de Notas.
rem
rem O variaveis.bat esta no .gitignore: ele NAO vai para o GitHub.
rem ------------------------------------------------------------------
rem Chave secreta do Django. Gere com:
rem python -c "import secrets; print(secrets.token_urlsafe(50))"
set SECRET_KEY=trocar
rem True so durante o desenvolvimento
set DEBUG=True
rem Banco de dados PostgreSQL (o banco e criado antes, no pgAdmin)
set DB_NAME=trocar
set DB_USER=postgres
set DB_PASSWORD=trocar
set DB_HOST=localhost
set DB_PORT=5432
echo Variaveis de ambiente carregadas.
