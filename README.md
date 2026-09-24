# xml-sitemap-analyzer

Point it at a domain and get every page the site publishes — sitemap discovery, platform detection, page metadata. No dependencies.

```
python sitemap_analyzer.py example.com
```

**[English](#english)** · **[Português](#portugues)**

---

<a id="english"></a>

# English

Give it a domain. It finds the site's XML sitemap, walks it, visits every page, and hands you an organized inventory.

Built on the Python standard library only — **no `pip install`, no virtualenv, nothing to set up** beyond Python itself.

## What it does

1. **Detects the platform** — WordPress, Shopify, Next.js, Drupal, Magento, Plone, Hugo and ~20 more, by cross-checking HTML, HTTP headers, `robots.txt` and sitemap naming.
2. **Finds the sitemap** — reads the `Sitemap:` line from `robots.txt` first; if absent, probes 10 well-known paths (`/sitemap.xml`, `/wp-sitemap.xml`, `/sitemap_index.xml`, …).
3. **Walks sitemaps recursively** — resolves nested `<sitemapindex>`, gzipped `.xml.gz` files, plain-text sitemaps and RSS/Atom feeds.
4. **Falls back to a link crawl** when the site has no sitemap, or when the declared one fails.
5. **Visits pages in parallel**, extracting title, meta description, `h1`, `canonical`, language, HTTP status and size.
6. **Organizes and prints it**, with a summary and a list of broken pages.

## Install

### Windows 11

**1. Install Python.** Open PowerShell (press `Windows`, type `powershell`, Enter) and check:

```powershell
python --version
```

If you see something like `Python 3.12.1`, skip ahead. If it opens the Microsoft Store or errors out, install it:

- **Microsoft Store** (easiest) — search for `Python 3.12` and click Install. It sets up PATH for you.
- **[python.org/downloads](https://www.python.org/downloads/)** — run the installer and **tick "Add python.exe to PATH"** on the first screen, before clicking Install.

> Missing that checkbox is the single most common setup problem. If you skipped it, re-run the installer, choose **Modify**, and enable the option.

**2. Get the project.** Click the green **Code** button above → **Download ZIP** → right-click the file → **Extract All**. Or with Git:

```powershell
cd $HOME\Documents
git clone https://github.com/MrMarkinBoladao/xml-sitemap-analyzer.git
```

**3. Run it.** Open the extracted folder, right-click an empty spot → **Open in Terminal**, then:

```powershell
python sitemap_analyzer.py example.com
```

Prefer not to type commands? **Double-click `analyze.bat`.** It asks for the domain, detects whether you have `python` or `py`, and waits before closing so you can read the output.

### macOS / Linux

```bash
git clone https://github.com/MrMarkinBoladao/xml-sitemap-analyzer.git
cd xml-sitemap-analyzer
python3 sitemap_analyzer.py example.com
```

## Usage

```
python sitemap_analyzer.py DOMAIN
```

Works with or without `https://`, with or without `www`:

```powershell
python sitemap_analyzer.py example.com
python sitemap_analyzer.py https://www.example.com/
```

### Sample output

Illustrative, from a fictional WordPress site:

```
============================================================================================
  example.com
  Example Store - Handmade goods
============================================================================================

DETECTION
  Final URL ........ https://example.com/
  Status ........... 200
  Platform ......... WordPress
  Generator ........ WordPress 6.7.1
  Server ........... nginx
  Language ......... en-US
  robots.txt ....... found
  Sitemap via ...... robots.txt
  URLs in total .... 24

SITEMAPS READ (5)
  - https://example.com/wp-sitemap.xml
  - https://example.com/wp-sitemap-posts-post-1.xml
  - https://example.com/wp-sitemap-posts-page-1.xml
  - https://example.com/wp-sitemap-taxonomies-category-1.xml
  - https://example.com/wp-sitemap-users-1.xml

FEEDS
  - https://example.com/feed/
  - https://example.com/comments/feed/

APIS AVAILABLE
  - https://example.com/wp-json/wp/v2/posts

wp-sitemap-posts-post-1.xml  (12)
    1. How to pick the right size - Example Store
       https://example.com/blog/picking-a-size/
       mod: 2026-09-01 | 200 | 62.1 KB
       A short guide to measuring before you order.
    2. Care instructions - Example Store
       https://example.com/blog/care/
       mod: 2026-08-18 | 200 | 48.7 KB
    ...

wp-sitemap-posts-page-1.xml  (8)
   13. About the shop - Example Store
       https://example.com/about/
       mod: 2026-07-24 | 200 | 51.3 KB
   14. Contact - Example Store
       https://example.com/contact/
       mod: 2026-08-12 | 200 | 38.0 KB
    ...

SUMMARY
  URLs found .............. 24
  Pages inspected ......... 24
  OK responses ............ 24
  With problems ........... 0
  Groups .................. 4
  Time .................... 3.4s
```

Reading it:

| Block | Meaning |
|---|---|
| `DETECTION` | Which technology runs the site, and where the sitemap was found |
| `SITEMAPS READ` | Every XML walked, including nested ones |
| `FEEDS` | Available RSS/Atom |
| `APIS AVAILABLE` | Open JSON endpoints (e.g. the WordPress REST API) |
| page list | Title, URL, last-modified date, HTTP status, size |
| `SUMMARY` | Overall counts |
| `PROBLEMS` | Only shown when a page errored or 4xx/5xx'd |
| `WARNINGS` | Only shown when something went sideways (e.g. a blocked sitemap) |

### Output in Portuguese

```powershell
python sitemap_analyzer.py example.com --lang pt
```

On Windows there is a shortcut for this: **`analisar.bat`**.

### Saving results

```powershell
python sitemap_analyzer.py example.com --csv pages.csv     # spreadsheet
python sitemap_analyzer.py example.com --json site.json    # full report
python sitemap_analyzer.py example.com > report.txt        # plain text
```

> **Garbled accents in Excel?** The CSV is UTF-8. Use **Data → Get Data → From Text/CSV** and pick UTF-8 as the origin, instead of double-clicking the file.

### Recipes

```powershell
# Fast: URLs only, without visiting each page
python sitemap_analyzer.py example.com --no-meta

# Hunt for broken links across the whole site
python sitemap_analyzer.py example.com --limit 0

# One section only
python sitemap_analyzer.py example.com --include "/blog/"

# Drop the noise
python sitemap_analyzer.py example.com --exclude "/tag/|/author/"

# Large site: cap the work
python sitemap_analyzer.py example.com --limit 50 --max-urls 500

# Go slow, for a small server
python sitemap_analyzer.py example.com --workers 2 --delay 0.5

# Sweep everything on a site you own, ignoring robots.txt
python sitemap_analyzer.py example.com --ignore-robots
```

## Options

| Flag | Default | What it does |
|---|---|---|
| `--limit N` | 200 | Max pages inspected (`0` = no limit) |
| `--max-urls N` | no limit | Stop reading sitemaps after N URLs |
| `--no-meta` | — | Don't visit pages; list only what the sitemap reports |
| `--quick` | — | Skip feed and API probing |
| `--sitemap URL` | — | Use this sitemap instead of detecting one |
| `--include REGEX` | — | Keep only matching URLs |
| `--exclude REGEX` | — | Drop matching URLs |
| `--group-by` | `auto` | `auto`, `sitemap` or `section` |
| `--depth N` | 6 | Max sitemap index depth |
| `--crawl-depth N` | 2 | Link crawl depth when there is no sitemap |
| `--workers N` | 8 | Parallel requests |
| `--timeout S` | 15 | Per-request timeout, seconds |
| `--retries N` | 1 | Extra attempts per request |
| `--delay S` | 0 | Pause before each request |
| `--ignore-robots` | — | Ignore `robots.txt` Disallow rules |
| `--user-agent S` | `sitemap-analyzer/1.0` | Custom User-Agent |
| `--lang` | `en` | Output language: `en` or `pt` |
| `--json FILE` | — | Save the full report as JSON |
| `--csv FILE` | — | Save the page list as CSV |
| `--no-color` | — | Disable colors |
| `--help` | — | Show help |

`--group-by auto` uses `sitemap` when the site has more than one sitemap (separating posts, pages, categories) and `section` when it has only one (grouping by first URL segment).

## Behavior notes

- **Respects `robots.txt` by default.** Disallowed URLs appear in the list marked `skipped`, and are never downloaded. Use `--ignore-robots` only on sites you own.
- **Follows host redirects.** If `example.com` redirects to `www.example.com`, everything is re-based on the final host before looking for the sitemap.
- **Never lies about provenance.** If the declared sitemap returns 403/404, `Sitemap via` reads `link crawl (declared sitemap failed)` and the real reason shows up under `WARNINGS`.
- **600 KB ceiling per response** — enough for metadata, and it won't accidentally pull down a huge PDF.
- **Exit codes:** `0` success, `1` homepage unreachable, `2` invalid domain.

## Limitations

- Client-rendered sites (SPAs without SSR) may return empty titles and descriptions — this tool does not execute JavaScript.
- A sitemap behind Cloudflare or a WAF will return 403; the tool then falls back to crawling, which yields fewer URLs.
- Platform detection is fingerprint-based, so it may report more than one technology (e.g. `WordPress, Cloudflare`). That's expected — they are different layers.

## Requirements

Python 3.8+. No external libraries. Same behavior on Windows, macOS and Linux — on macOS and Linux the command is `python3` instead of `python`.

---

<a id="portugues"></a>

# Português

Você dá um domínio. Ele acha o sitemap XML do site, percorre, visita cada página e devolve um inventário organizado.

Feito só com a biblioteca padrão do Python — **sem `pip install`, sem virtualenv, nada pra configurar** além do Python.

## O que ele faz

1. **Detecta a plataforma** — WordPress, Shopify, Next.js, Drupal, Magento, Plone, Hugo e mais uns 20, cruzando HTML, headers HTTP, `robots.txt` e o nome do sitemap.
2. **Acha o sitemap** — primeiro lê a linha `Sitemap:` do `robots.txt`; se não houver, testa 10 caminhos conhecidos (`/sitemap.xml`, `/wp-sitemap.xml`, `/sitemap_index.xml`, …).
3. **Percorre os sitemaps recursivamente** — resolve `<sitemapindex>` aninhado, arquivos `.xml.gz` comprimidos, sitemaps em texto puro e feeds RSS/Atom.
4. **Cai para um crawl de links** quando o site não tem sitemap, ou quando o declarado falha.
5. **Visita as páginas em paralelo**, extraindo título, meta description, `h1`, `canonical`, idioma, status HTTP e tamanho.
6. **Organiza e imprime**, com resumo e lista de páginas quebradas.

## Instalando

### Windows 11

**1. Instale o Python.** Abra o PowerShell (tecla `Windows`, digite `powershell`, Enter) e teste:

```powershell
python --version
```

Se aparecer algo como `Python 3.12.1`, pule adiante. Se abrir a Microsoft Store ou der erro, instale:

- **Microsoft Store** (mais fácil) — busque por `Python 3.12` e clique em Instalar. Ela já configura o PATH.
- **[python.org/downloads](https://www.python.org/downloads/)** — rode o instalador e **marque "Add python.exe to PATH"** na primeira tela, antes de clicar em Install.

> Esquecer essa caixinha é de longe o problema mais comum. Se você passou batido, rode o instalador de novo, escolha **Modify** e ative a opção.

**2. Baixe o projeto.** Clique no botão verde **Code** acima → **Download ZIP** → botão direito no arquivo → **Extrair tudo**. Ou com Git:

```powershell
cd $HOME\Documents
git clone https://github.com/MrMarkinBoladao/xml-sitemap-analyzer.git
```

**3. Rode.** Abra a pasta extraída, clique com o botão direito num espaço vazio → **Abrir no Terminal**, e:

```powershell
python sitemap_analyzer.py exemplo.com --lang pt
```

Não quer digitar comando? **Dê dois cliques em `analisar.bat`.** Ele pergunta o domínio, detecta se você tem `python` ou `py`, já usa português, e espera antes de fechar pra você conseguir ler.

### macOS / Linux

```bash
git clone https://github.com/MrMarkinBoladao/xml-sitemap-analyzer.git
cd xml-sitemap-analyzer
python3 sitemap_analyzer.py exemplo.com --lang pt
```

## Usando

```
python sitemap_analyzer.py DOMINIO --lang pt
```

A saída padrão é em inglês. O `--lang pt` traz tudo pra português — inclusive o `--help`:

```powershell
python sitemap_analyzer.py --lang pt --help
```

Funciona com ou sem `https://`, com ou sem `www`:

```powershell
python sitemap_analyzer.py exemplo.com --lang pt
python sitemap_analyzer.py https://www.exemplo.com/ --lang pt
```

### Exemplo de saída

Ilustrativo, de um site WordPress fictício:

```
============================================================================================
  exemplo.com
  Loja Exemplo - Produtos artesanais
============================================================================================

DETECCAO
  URL final ........ https://exemplo.com/
  Status ........... 200
  Plataforma ....... WordPress
  Generator ........ WordPress 6.7.1
  Servidor ......... nginx
  Idioma ........... pt-BR
  robots.txt ....... encontrado
  Sitemap via ...... robots.txt
  URLs no total .... 24

SITEMAPS LIDOS (5)
  - https://exemplo.com/wp-sitemap.xml
  - https://exemplo.com/wp-sitemap-posts-post-1.xml
  - https://exemplo.com/wp-sitemap-posts-page-1.xml
  - https://exemplo.com/wp-sitemap-taxonomies-category-1.xml
  - https://exemplo.com/wp-sitemap-users-1.xml

FEEDS
  - https://exemplo.com/feed/
  - https://exemplo.com/comments/feed/

APIS DISPONIVEIS
  - https://exemplo.com/wp-json/wp/v2/posts

wp-sitemap-posts-post-1.xml  (12)
    1. Como escolher o tamanho certo - Loja Exemplo
       https://exemplo.com/blog/escolher-tamanho/
       mod: 2026-09-01 | 200 | 62.1 KB
       Um guia rapido de como medir antes de pedir.
    2. Instrucoes de cuidado - Loja Exemplo
       https://exemplo.com/blog/cuidados/
       mod: 2026-08-18 | 200 | 48.7 KB
    ...

wp-sitemap-posts-page-1.xml  (8)
   13. Sobre a loja - Loja Exemplo
       https://exemplo.com/sobre/
       mod: 2026-07-24 | 200 | 51.3 KB
   14. Contato - Loja Exemplo
       https://exemplo.com/contato/
       mod: 2026-08-12 | 200 | 38.0 KB
    ...

RESUMO
  URLs encontradas ........ 24
  Paginas inspecionadas ... 24
  Respostas OK ............ 24
  Com problema ............ 0
  Grupos .................. 4
  Tempo ................... 3.4s
```

Lendo o relatório:

| Bloco | O que é |
|---|---|
| `DETECCAO` | Qual tecnologia roda o site e onde o sitemap foi achado |
| `SITEMAPS LIDOS` | Todos os XMLs percorridos, inclusive os aninhados |
| `FEEDS` | RSS/Atom disponíveis |
| `APIS DISPONIVEIS` | Endpoints JSON abertos (ex: API REST do WordPress) |
| lista de páginas | Título, URL, data de modificação, status HTTP e tamanho |
| `RESUMO` | Contagens gerais |
| `PROBLEMAS` | Só aparece se alguma página deu erro ou 4xx/5xx |
| `AVISOS` | Só aparece se algo não saiu como esperado (ex: sitemap bloqueado) |

### Salvando o resultado

```powershell
python sitemap_analyzer.py exemplo.com --lang pt --csv paginas.csv   # planilha
python sitemap_analyzer.py exemplo.com --lang pt --json site.json    # relatorio completo
python sitemap_analyzer.py exemplo.com --lang pt > relatorio.txt     # texto
```

Pra abrir o CSV direto: `start paginas.csv`

> **Acentos estranhos no Excel?** O CSV é UTF-8. Use **Dados → Obter Dados → De Texto/CSV** e escolha a origem UTF-8, em vez de dar dois cliques no arquivo.

### Receitas

```powershell
# Rapido: so as URLs, sem visitar cada pagina
python sitemap_analyzer.py exemplo.com --lang pt --no-meta

# Cacar links quebrados no site todo
python sitemap_analyzer.py exemplo.com --lang pt --limit 0

# So uma secao
python sitemap_analyzer.py exemplo.com --lang pt --include "/blog/"

# Ignorar ruido
python sitemap_analyzer.py exemplo.com --lang pt --exclude "/tag/|/author/"

# Site grande: limita o trabalho
python sitemap_analyzer.py exemplo.com --lang pt --limit 50 --max-urls 500

# Devagar, pra nao incomodar um servidor pequeno
python sitemap_analyzer.py exemplo.com --lang pt --workers 2 --delay 0.5

# Varrer tudo num site seu, ignorando o robots.txt
python sitemap_analyzer.py exemplo.com --lang pt --ignore-robots
```

## Problemas comuns no Windows

**`python` não é reconhecido como comando.** O Python não está no PATH. Tente `py sitemap_analyzer.py exemplo.com --lang pt`. Se o `py` funcionar, use ele em tudo. Se nenhum funcionar, reinstale marcando "Add python.exe to PATH".

**Abre a Microsoft Store em vez de rodar.** O Windows 11 tem um atalho falso de `python` que só abre a Store. Instale o Python de verdade, ou desative em **Configurações → Aplicativos → Configurações de aplicativo avançadas → Aliases de execução de aplicativo**, desligando `python.exe` e `python3.exe`.

**`can't open file 'sitemap_analyzer.py'`.** Você está na pasta errada. Rode `dir` pra ver onde está; se o arquivo não aparecer, navegue até a pasta do projeto com `cd`.

**A saída vem cheia de códigos tipo `←[36m`.** Console antigo sem suporte a cores. Use `--no-color`. O Windows Terminal (padrão no Windows 11) mostra as cores certas.

**Trava ou fica muito lento.** Site grande demais: `--no-meta --limit 30 --timeout 8`. Pra interromper, `Ctrl + C`.

**Erro de SSL ou certificado.** Costuma ser antivírus ou proxy corporativo interceptando HTTPS. Teste em outra rede, ou veja se seu antivírus tem "inspeção de HTTPS/SSL" ligada.

## Opções

| Flag | Padrão | O que faz |
|---|---|---|
| `--limit N` | 200 | Máximo de páginas inspecionadas (`0` = sem limite) |
| `--max-urls N` | sem limite | Para de ler sitemaps depois de N URLs |
| `--no-meta` | — | Não visita as páginas; lista só o que o sitemap informa |
| `--quick` | — | Pula a sondagem de feeds e APIs |
| `--sitemap URL` | — | Usa este sitemap em vez de detectar |
| `--include REGEX` | — | Só URLs que casarem |
| `--exclude REGEX` | — | Descarta URLs que casarem |
| `--group-by` | `auto` | `auto`, `sitemap` ou `section` |
| `--depth N` | 6 | Profundidade máxima de sitemap index |
| `--crawl-depth N` | 2 | Profundidade do crawl quando não há sitemap |
| `--workers N` | 8 | Requisições em paralelo |
| `--timeout S` | 15 | Timeout por requisição, em segundos |
| `--retries N` | 1 | Tentativas extras por requisição |
| `--delay S` | 0 | Pausa antes de cada requisição |
| `--ignore-robots` | — | Ignora as regras `Disallow` do `robots.txt` |
| `--user-agent S` | `sitemap-analyzer/1.0` | User-Agent customizado |
| `--lang` | `en` | Idioma da saída: `en` ou `pt` |
| `--json ARQ` | — | Salva o relatório completo em JSON |
| `--csv ARQ` | — | Salva a lista de páginas em CSV |
| `--no-color` | — | Desliga as cores |
| `--help` | — | Mostra a ajuda |

`--group-by auto` usa `sitemap` quando o site tem mais de um sitemap (separando posts, páginas, categorias) e `section` quando tem só um (agrupando pelo primeiro segmento da URL).

## Detalhes de comportamento

- **Respeita o `robots.txt` por padrão.** URLs bloqueadas aparecem na lista marcadas como `pulado`, e nunca são baixadas. Use `--ignore-robots` só em site seu.
- **Segue redirect de host.** Se `exemplo.com` redireciona pra `www.exemplo.com`, tudo é rebaseado no host final antes de procurar o sitemap.
- **Não mente sobre a origem dos dados.** Se o sitemap declarado der 403/404, o campo `Sitemap via` diz `crawl de links (sitemap declarado falhou)` e o motivo real aparece em `AVISOS`.
- **Teto de 600 KB por resposta** — suficiente pra metadados, e não baixa um PDF gigante por acidente.
- **Códigos de saída:** `0` sucesso, `1` homepage não respondeu, `2` domínio inválido.

## Limitações

- Sites renderizados no navegador (SPA sem SSR) podem devolver título e description vazios — o script não executa JavaScript.
- Sitemap atrás de Cloudflare ou WAF devolve 403; aí ele cai pro crawl, que rende menos URLs.
- A detecção de plataforma é por fingerprint, então pode listar mais de uma tecnologia (ex: `WordPress, Cloudflare`). Isso é esperado — são camadas diferentes.

## Requisitos

Python 3.8 ou superior. Nenhuma biblioteca externa. Mesmo comportamento em Windows, macOS e Linux — em macOS e Linux o comando é `python3` em vez de `python`.
