# Backend — Django + DRF

Ainda não inicializado (Bloco 0.2). Plano:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
django-admin startproject config .
python manage.py migrate && python manage.py runserver
```

Apps previstos em `apps/`: `core`, `usuarios`, `produtos`, `estoque`,
`vendas`, `clientes`, `fornecedores`, `financeiro`.
