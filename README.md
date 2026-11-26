# Caderno de Notas

Sistema web para criar e organizar anotações, com foco em segurança e
privacidade. Projeto integrador das disciplinas de Engenharia de Software,
Banco de Dados e Linguagens de Programação.

## Funcionalidades

- Cadastro, login e logout, com senha em hash (PBKDF2, padrão do Django)
- Cadernos, notas e etiquetas (cada usuário vê só os próprios dados)
- Busca de notas por texto, caderno, etiqueta, período e tipo
- Nota protegida por senha: conteúdo cifrado com AES-256-GCM e chave derivada por PBKDF2
- Senha de estresse: entra normalmente, mas apaga os dados do usuário
- Gerador de passphrases (Diceware) e medidor de força de senha por entropia
- Painel administrativo com inlines

## Tecnologias

Python 3.11, Django 5.2, PostgreSQL (14 ou mais novo), HTML, CSS e
Bootstrap 5.3. Biblioteca extra: `cryptography`.

## Como rodar (Prompt de Comando do Windows)

**1. Baixar o projeto e instalar as dependências**

```
git clone <endereço do repositório>
cd caderno_notas
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**2. Criar o banco de dados**

No pgAdmin, crie um banco vazio chamado `caderno_notas`.

**3. Configurar as variáveis de ambiente**

Os segredos (chave do Django e senha do banco) não ficam no código.
Copie o arquivo de exemplo e preencha a cópia:

```
copy variaveis.exemplo.bat variaveis.bat
notepad variaveis.bat
```

Para gerar a `SECRET_KEY`:

```
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Depois carregue as variáveis. **Isso precisa ser repetido toda vez que
abrir um Prompt de Comando novo:**

```
variaveis.bat
```

O arquivo `variaveis.bat` está no `.gitignore` e nunca deve ir para o GitHub.

**4. Criar as tabelas e o administrador**

```
python manage.py migrate
python manage.py criar_admin
```

O comando `criar_admin` sorteia a senha do administrador com o gerador
Diceware do próprio sistema e mostra essa senha uma única vez. Anote.

**5. (Opcional) Criar dados de demonstração**

```
python manage.py popular_demo
```

Cria o usuário `demo` com cadernos, etiquetas, notas e uma nota protegida.
As senhas aparecem no terminal.

**6. Rodar**

```
python manage.py runserver
```

- Sistema: http://127.0.0.1:8000/
- Painel administrativo: http://127.0.0.1:8000/admin/

## Testes

```
python manage.py test
```

São 41 testes: cifra, entropia, Diceware, isolamento entre usuários, notas
protegidas e senha de estresse. Demoram cerca de 20 segundos, porque cada
senha passa por 1.000.000 de repetições do PBKDF2, como no uso real.

## Estrutura

```
config/                 configurações (settings.py) e rotas (urls.py)
app/
    models.py           tabelas: Usuario, Caderno, Etiqueta, Nota, NotaComum, NotaProtegida
    views.py            telas (classes com get e post)
    forms.py            formulários
    admin.py            painel administrativo e inlines
    cifra.py            PBKDF2 + AES-256-GCM das notas protegidas
    entropia.py         medidor de força e validador de senha
    diceware.py         gerador de passphrases
    backends.py         login com a senha de estresse
    tests.py            testes automáticos
    dados/dadoware.txt  lista de 7.776 palavras
    management/commands criar_admin e popular_demo
    static/app          Bootstrap 5.3 e CSS próprio
    templates/app       páginas HTML
```

## Limitações conhecidas

- A busca não encontra texto dentro de notas protegidas.
- Senha de nota esquecida significa nota perdida: não existe recuperação.
- O apagamento da senha de estresse usa DELETE. Não é apagamento forense:
  os dados podem continuar no disco, no WAL e em backups.
- Notas comuns, títulos e etiquetas ficam legíveis para quem tem acesso ao
  banco, inclusive o administrador.
- O login não limita o número de tentativas.
- O medidor de entropia mede o formato da senha, não o quanto ela é
  previsível: "Senha1234!" é aceita.
- O `runserver` usa HTTP. Um uso real exigiria HTTPS.

## Créditos e licenças

**Lista de palavras Dadoware** (`app/dados/dadoware.txt`): segunda edição
da lista do projeto [Dadoware](https://github.com/thoughtworks/dadoware),
da ThoughtWorks Brasil. Texto, miolo e código de Luciano Ramalho; revisão
e seleção de palavras por Ana Paula Gomes, Anna Cruz, Bonifacio de
Oliveira, Denis Costa, Guilherme Prestes, Henrique Souza, Marcelo Schmidt,
Mariana Bravo, Nayara Moura, Pedro Evangelista, Roberto Soares, Thais
Siqueira, Tiago Megale, Tulio Casagrande e Vitor Gomes. Licença
[Creative Commons Atribuição-NãoComercial 3.0](https://github.com/thoughtworks/dadoware/blob/master/LICENSE.md).
A lista foi usada sem alterações nas palavras (só foi removida a coluna
com os números dos dados). Este projeto é acadêmico e não tem fins
comerciais.

**Bootstrap 5.3** (`app/static/app`): licença MIT.
