# Decisões técnicas

Cada decisão com alternativas reais fica aqui. As decisões não se apagam: se uma for revista, acrescenta-se uma nova que a substitui e indica-se qual.

Formato:
```
## D-00X: <título>
Data: AAAA-MM-DD
Contexto: <o problema>
Opções: <A, B, C>
Escolha: <qual>
Porquê: <razões e trade-offs>
```

---

## D-001: QR code antes do LLM
Data: 2026-11-23
Contexto: os campos fiscais de uma fatura podem ser lidos do QR code da AT ou por um modelo de linguagem que lê a imagem.
Opções: A) LLM para tudo; B) QR primeiro, LLM só para o que falta.
Escolha: B.
Porquê: o QR tem os campos fiscais estruturados (especificação da AT) e a leitura é determinística, grátis e testável. O LLM custa dinheiro, demora e pode errar. Só entra quando o QR falta ou é ilegível.

## D-002: núcleo puro
Data: 2026-11-23
Contexto: o pipeline precisa de ser testado e avaliado muitas vezes, e o destino dos dados muda entre a fase 1 (Supabase) e a fase 2 (Primavera).
Opções: A) pipeline que lê e escreve diretamente na base de dados; B) núcleo que recebe bytes e contexto e devolve um resultado, com a persistência à parte.
Escolha: B.
Porquê: testes rápidos e sem infraestrutura, avaliação (`scripts/avaliar.py`) que corre sem base de dados, e o destino dos dados troca-se sem tocar no núcleo. O custo é ter de passar o contexto explicitamente.

## D-003: alertas não são estados
Data: 2026-11-23
Contexto: uma fatura pode ter problemas (duplicado, IVA que não bate, NIF inválido) enquanto avança no processo.
Opções: A) um estado por problema; B) estados só para o processo e uma lista de alertas em cada fatura.
Escolha: B.
Porquê: uma fatura pode ter vários problemas ao mesmo tempo; misturá-los com o estado multiplicaria os estados e as transições. A severidade `bloqueante` dá o efeito de "parar" sem criar estados novos.

## D-004: `Decimal` para dinheiro
Data: 2026-11-23
Contexto: os valores das faturas são somados e comparados ao cêntimo.
Opções: A) `float`; B) `Decimal`; C) inteiros em cêntimos.
Escolha: B.
Porquê: `float` não representa valores como 0,1 com exatidão, e numa soma de faturas isso gera erros de cêntimos. Cêntimos inteiros também resolvem, mas obrigam a converter em cada entrada e saída; `Decimal` lê diretamente o texto do QR (`"12000.00"`) e o Pydantic suporta-o.

## D-005: taxas de IVA com vigência
Data: 2026-11-23
Contexto: a taxa de IVA depende do espaço fiscal (PT, PT-AC, PT-MA) e da data da fatura.
Opções: A) uma tabela fixa com as taxas atuais; B) períodos de vigência por espaço fiscal.
Escolha: B.
Porquê: o exemplo oficial da AT de 2019 usa 18 % nos Açores, e hoje são 16 %. Com taxas fixas, uma fatura antiga daria `IVA_NAO_BATE` sem razão.

## D-006: o frontend só fala com a API
Data: 2026-11-23
Contexto: o frontend podia ler e escrever diretamente na Supabase (com RLS) ou passar sempre pelo backend.
Opções: A) frontend com acesso direto às tabelas; B) Supabase no frontend só para o login, tudo o resto pela API.
Escolha: B.
Porquê: as regras de negócio (transições de estado, alertas bloqueantes) e as permissões ficam num único sítio, no backend, testadas em Python. O custo é escrever mais rotas na API.

## D-007: um ramo por sprint, commits com a referência da tarefa
Data: 2026-11-23
Contexto: o trabalho está organizado em sprints semanais e tarefas (`S1.1`, `S1.2`, ...). O histórico do Git deve mostrar essa divisão.
Opções: A) tudo no `main`; B) um ramo por sprint (`sprint-N`) com merge e tag no fim do sprint; C) um ramo e um pull request por tarefa, com issues e milestones no GitHub.
Escolha: B.
Porquê: o `main` só recebe sprints fechados, o que corresponde às demos de domingo; a tag `sprint-N` marca o estado de cada demo; o prefixo `S1.4:` permite `git log --grep "S1.4"`. A opção C mostra mais "processo" num portefólio, mas para uma pessoa sozinha é burocracia sem revisor. Pode ser adotada mais tarde sem mudar nada do que já existe.

## D-008: chaves novas da Supabase (publishable e secret)
Data: 2026-11-23
Contexto: o plano usava `SUPABASE_ANON_KEY` e `SUPABASE_SERVICE_ROLE_KEY`. A Supabase está a substituir estas chaves (JWT antigos) por chaves `sb_publishable_...` e `sb_secret_...`, e anuncia a retirada das antigas para o fim de 2026. Fonte: https://supabase.com/docs/guides/getting-started/migrating-to-new-api-keys
Opções: A) manter as chaves antigas; B) usar as chaves novas, mas manter os nomes antigos das variáveis; C) usar as chaves novas com nomes novos (`SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`).
Escolha: C.
Porquê: A deixaria de funcionar em pouco tempo. B funcionaria (as chaves novas são aceites onde se usavam as antigas), mas o nome da variável não corresponderia ao que o painel mostra. Com C, o nome diz o que lá está. A chave secreta continua a ignorar o RLS, por isso só existe no backend.


## D-009: `uv.lock` no repositório
Data: 2026-11-23
Contexto: o `pyproject.toml` só indica versões mínimas (`>=`). Sem mais nada, cada instalação pode trazer versões diferentes das dependências e das dependências delas.
Opções: A) só o `pyproject.toml`; B) `pyproject.toml` e `uv.lock` no repositório.
Escolha: B.
Porquê: o lockfile fixa a versão exata de todos os pacotes (66 neste momento), por isso o meu PC, os testes e o deploy no Render instalam o mesmo. A opção A faz sentido para uma biblioteca publicada no PyPI, que tem de funcionar com várias versões. Para uma aplicação, interessa ser reprodutível. 
Para atualizar dependências: `uv lock --upgrade`, correr os testes e fazer commit do lockfile.

## D-010: regras do ruff
Data: 2026-11-23
Contexto: o ruff faz o lint e a formatação. É preciso escolher que regras aplicar e o comprimento máximo da linha.
Opções: A) regras por defeito (`E4`, `E7`, `E9`, `F`); B) um conjunto escolhido: `E`, `W`, `F`, `I`, `UP`, `B`, `SIM`; C) `ALL`.
Escolha: B, com `line-length = 100`.
Porquê: A não ordena imports nem apanha bugs comuns (`B`). C ativa centenas de regras, muitas delas de opinião, e gera ruído para quem está a aprender. B cobre o estilo PEP 8, os erros reais, a ordem dos imports, a sintaxe moderna do Python 3.12, os bugs prováveis e as simplificações. Usamos 100 caracteres em vez de 88 porque os nomes em português são longos (`NIF_ADQUIRENTE_DIFERENTE`, `segundos_em_conferencia`).