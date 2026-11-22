# Regras fiscais usadas no projeto

Referência para o código. Cada regra indica a fonte e se foi confirmada. Verificado a 22/11/2026.
Antes de aplicar o projeto a uma empresa real, rever as secções marcadas **por confirmar**.

---

## 1. Código QR das faturas

**Fonte:** AT, *Especificações Técnicas — Código QR*, v1.1, outubro de 2020 (Portaria n.º 195/2020).
https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/Novas_regras_faturacao/Documents/Especificacoes_Tecnicas_Codigo_QR.pdf

### Estrutura
- Cada campo é `Código:Valor`.
- Campos separados por `*`, pela ordem da tabela abaixo. Campos opcionais sem valor não aparecem.
- Valores monetários em euros, ponto decimal, sempre 2 casas, sem separador de milhares.
- Datas no formato `AAAAMMDD`.
- O campo `S` usa `;` para separar subcampos e não pode conter `*`.

### Campos

| Código | Conteúdo | Obrigatório |
| --- | --- | --- |
| A | NIF do emitente (9 dígitos, sem prefixo de país) | Sim |
| B | NIF do adquirente (`999999990` = consumidor final) | Sim |
| C | País do adquirente (ex.: `PT`) | Sim |
| D | Tipo de documento (ex.: `FT`, `FS`, `FR`, `NC`, `ND`) | Sim |
| E | Estado do documento (ex.: `N`) | Sim |
| F | Data do documento (`AAAAMMDD`) | Sim |
| G | Identificação única do documento (ex.: `FT AB2019/0035`) | Sim |
| H | ATCUD | Sim |
| I1 | Primeiro espaço fiscal (`PT`, `PT-AC`, `PT-MA` ou outro país); `I1:0` se não houver taxa de IVA | Sim |
| I2 | Base isenta | Não |
| I3 / I4 | Base / IVA à taxa reduzida | Não |
| I5 / I6 | Base / IVA à taxa intermédia | Não |
| I7 / I8 | Base / IVA à taxa normal | Não |
| J1–J8 | Segundo espaço fiscal, mesma lógica de I1–I8 | Não |
| K1–K8 | Terceiro espaço fiscal, mesma lógica de I1–I8 | Não |
| L | Não sujeito / não tributável em IVA | Não |
| M | Imposto do Selo | Não |
| N | Total de impostos (IVA + Imposto do Selo) | Sim |
| O | Total do documento com impostos | Sim |
| P | Retenção na fonte | Não |
| Q | 4 caracteres do hash | Sim |
| R | Número do certificado do programa | Sim |
| S | Outras informações (ex.: IBAN) | Não |

**Atenção:** os grupos I, J e K não estão presos a uma região. A região de cada grupo é dada pelo seu campo 1 (`I1`, `J1`, `K1`). O parser tem de ler esse código, não assumir que J é sempre Açores.

### Exemplo oficial (Exemplo 1 da especificação)

```
A:123456789*B:999999990*C:PT*D:FT*E:N*F:20191231*G:FT AB2019/0035*H:CSDF7T5H-0035*I1:PT*I2:12000.00*I3:15000.00*I4:900.00*I5:50000.00*I6:6500.00*I7:80000.00*I8:18400.00*J1:PT-AC*J2:10000.00*J3:25000.56*J4:1000.02*J5:75000.00*J6:6750.00*J7:100000.00*J8:18000.00*K1:PT-MA*K2:5000.00*K3:12500.00*K4:625.00*K5:25000.00*K6:3000.00*K7:40000.00*K8:8800.00*L:100.00*M:25.00*N:64000.02*O:513600.58*P:100.00*Q:kLp0*R:9999*S:TB;PT00000000000000000000000;513500.58
```

Usar esta string como teste do parser. Contas verificadas a correr código:
- soma dos IVA de I, J e K + M (25,00) = 64 000,02 = `N`
- soma de todas as bases (I2, I3, I5, I7 e equivalentes em J e K) + L + N = 513 600,58 = `O`
- a retenção `P` não entra no total `O`
- taxas implícitas: PT 6/13/23 %, PT-AC 4/9/18 %, PT-MA 5/12/22 % (taxas em vigor em dezembro de 2019; ver secção 4)
- no próprio documento da AT, o último valor do campo `S` (513 500,58) não coincide com `O`; não usar `S` para validar totais

### Regras de validação derivadas
- `N == soma(IVA de todos os grupos) + M` (tolerância 0,01 €)
- `O == soma(bases de todos os grupos) + L + N` (tolerância 0,01 €)
- IVA de cada escalão ≈ base × taxa do escalão, para o espaço fiscal e a data do documento (tolerância configurável; arredondamentos por linha podem gerar diferenças de cêntimos)

### Onde aparece e quando falta
- O QR deve estar no corpo da fatura, na primeira ou na última página, e o ATCUD imediatamente antes dele. Fonte: Sovos, resumo da Portaria 195/2020. → ler o QR em todas as páginas, começando pela primeira e pela última.
- Faturas manuais em impressos de tipografia autorizada não têm QR; o ATCUD continua obrigatório. Fonte: OCC, parecer técnico. https://occ.pt/en/node/13572 → é por isso que o projeto precisa do caminho com LLM.
- Dimensão mínima de 30 × 30 mm e correção de erros nível M (especificação da AT). Usar estes parâmetros no gerador de faturas sintéticas.

---

## 2. ATCUD

**Fonte:** Portaria n.º 195/2020, art. 3.º. https://diariodarepublica.pt/dr/detalhe/portaria/195-2020-140210523

- Formato: código de validação da série + `-` + número sequencial do documento na série. Exemplo: `CSDF7T5H-0035`.
- Obrigatório em todas as faturas e documentos fiscalmente relevantes, incluindo os emitidos por máquinas registadoras (FAQ da AT, faqs-00883).
- Validação no projeto: formato `^[A-Za-z0-9]+-[0-9]+$`. O código de validação é atribuído pela AT e não tem dígito de controlo público, por isso não é possível validar mais do que o formato.

---

## 3. NIF

Algoritmo público do dígito de controlo (módulo 11):
1. Multiplicar os 8 primeiros dígitos pelos pesos 9, 8, 7, 6, 5, 4, 3, 2 e somar.
2. `resto = soma mod 11`.
3. Dígito de controlo = `0` se `resto < 2`; caso contrário, `11 − resto`.

Testes (confirmados a correr código): `123456789` válido, `999999990` válido, `123456780` inválido.

Nota: um NIF com dígito de controlo válido pode pertencer a uma entidade real. Nas faturas sintéticas, usar nomes claramente fictícios e não publicar os NIF gerados como se fossem de empresas reais.

---

## 4. Taxas de IVA por região, com vigência

A taxa aplicável depende do espaço fiscal **e da data** do documento. A tabela `config/iva.yaml` tem de guardar períodos de vigência.

| Espaço fiscal | Período | Reduzida | Intermédia | Normal | Fonte |
| --- | --- | --- | --- | --- | --- |
| PT (Continente) | em vigor em 2026 | 6 % | 13 % | 23 % | PwC, Guia Fiscal 2026 |
| PT-AC (Açores) | desde 1/7/2021 | 4 % | 9 % | 16 % | Despacho SEAF 194/2021; Ofício-Circulado 30237/2021 |
| PT-AC (Açores) | antes de 1/7/2021 | 4 % | 9 % | 18 % | Garrigues (redução de 18 % para 16 %); exemplo da AT de 2019 |
| PT-MA (Madeira) | desde 1/10/2024 | 4 % | 12 % | 22 % | Ofício-Circulado 25045/2024 |
| PT-MA (Madeira) | antes de 1/10/2024 | 5 % | 12 % | 22 % | exemplo da AT de 2019; Ofício-Circulado 25045/2024 (12 % e 22 % desde 1/4/2012) |

**Por confirmar:** a data de início dos períodos "antes de". Só são usados no teste com o exemplo oficial da AT (dezembro de 2019). As faturas sintéticas do projeto são de 2025–2026.

Fontes:
- https://www.pwc.pt/pt/pwcinforfisco/guia-fiscal/2026/iva.html
- https://info.portaldasfinancas.gov.pt/pt/informacao_fiscal/legislacao/Despachos_SEAF/Documents/despacho_SEAF_194_2021_XXII.pdf
- https://info.portaldasfinancas.gov.pt/pt/informacao_fiscal/legislacao/instrucoes_administrativas/Documents/Oficio_circulado_25045_2024.pdf
- https://www.garrigues.com/pt/pt-PT/news/reducao-18-16-da-taxa-do-iva-nos-acores

Algumas páginas na internet ainda indicam 5 % como taxa reduzida da Madeira. O ofício-circulado da AT indica 4 % desde 1/10/2024; usar a fonte oficial.

---

## 5. e-Fatura

**Confirmado:**
- Os adquirentes consultam as faturas comunicadas pelos fornecedores em Portal das Finanças > e-Fatura > Faturação > Adquirente > Verificar Faturas (FAQ da AT, faqs-00984).
- **Exportação para CSV (confirmada a 22/11/2026, em fontes independentes):**
  - Caminho: e-Fatura > Adquirente > Consultar/Verificar Faturas > escolher datas > Pesquisar > **"Obter dados para Excel"**, que descarrega um `.csv`. Fontes: taxclara.pt (https://taxclara.pt/efatura-check), otimiza.pt (https://otimiza.pt/guia-efatura).
  - Limite de **300 documentos por exportação**. Com mais, exportar por períodos mais curtos. Fontes: Elabora Software (https://elabora.pt/ficheiros/WinContinSNC_-_Obter_e_lancar_documentos_do_site_e-fatura.pdf), taxclara.pt.
  - O ficheiro do lado do adquirente tem o mesmo formato do lado do emitente; do lado do emitente, o nome do cliente não vem preenchido por causa do RGPD. Fonte: Elabora Software (https://www.elabora.pt/ficheiros/WinContinSNC_-_Trabalhar_um_ficheiro_CSV.pdf).
  - Abrir e voltar a gravar o ficheiro no Excel pode mudar o formato; o importador deve receber o ficheiro tal como sai do portal. Fonte: taxclara.pt.
  - Vários programas de contabilidade importam este CSV (Elabora, ARTSOFT, Odoo com módulo da ThinkOpen, Fiscal Records), o que indica um formato estável na prática, mas não documentado pela AT.
- Alguns programas (Elabora, ARTSOFT) também obtêm os documentos entrando no portal com a senha da empresa guardada. **Este projeto não faz isso:** a funcionária exporta o CSV e carrega-o; o sistema nunca guarda nem usa a senha do Portal das Finanças.
- As faturas que o fornecedor não comunicou podem ser registadas pelo adquirente em "Registar Faturas" (mesma FAQ).
- Há alertas de divergências em e-Fatura > Faturação > Adquirente > Apoio ao Cumprimento > Divergências (FAQ da AT, faqs-00977).
- O webservice documentado pela AT serve para os **emitentes** comunicarem faturas, não para os adquirentes as consultarem (Manual de Integração de Software, 2022).
- O Cegid Primavera tem uma extensão de Compras que importa compras do e-Fatura e lê QR codes de documentos em pastas (página de ajuda da Cegid; edições Professional, Executive e Evolution). https://help.ila.cegid.com/primavera/docs/en/1619602435

**Por confirmar:**
- Com um ficheiro real: as colunas exatas, o separador e a codificação do CSV. Uma resposta de IA (Google, 22/11/2026, sem fonte primária verificada) descreve: emitente com NIF e designação social **na mesma coluna**; tipo e número do documento; ATCUD; data de emissão; total; IVA; base tributável; situação; valores com o símbolo `€` e **ponto como separador de milhares**. Tratar como hipótese até ver um ficheiro real.
- Forma rápida de confirmar sem dados da empresa: exportar o CSV do teu próprio NIF, como consumidor (o formato do adquirente é o mesmo). Guardar em `privado/`, nunca no repositório.
- Se existe alguma API oficial de consulta para adquirentes. Não encontrei nenhuma.
- Se a empresa real já usa a importação do e-Fatura do Primavera. Se usar, parte do lançamento já está automatizada, e o valor do projeto passa a estar na conferência, no arquivo digital e na aprovação.

---

## 6. Faturas em PDF e assinatura eletrónica qualificada

- Até 31/12/2026, as faturas em PDF sem assinatura são aceites como faturas eletrónicas (OE2026; Sage, Cegid).
- A proposta de Orçamento do Estado para 2027, entregue a 8/10/2026, prolonga essa aceitação até 31/12/2027. A votação final global está prevista para 24/11/2026. Fonte: InvoiceXpress, 19/11/2026. https://invoicexpress.com/?p=34858
- **Por confirmar** depois de 24/11/2026: se o prolongamento foi aprovado.
- Implicação para o projeto: nenhuma de imediato. No futuro, PDFs com assinatura qualificada ou faturas estruturadas (CIUS-PT) podem ser lidos sem IA.

---

## 7. Dedução do IVA

- Art. 19.º do CIVA: só confere direito à dedução o IVA em faturas passadas em forma legal, em nome e na posse do sujeito passivo (OCC, parecer técnico). https://www.occ.pt/index.php/en/node/50084
- Não encontrei nenhuma regra que faça depender a dedução da comunicação da fatura ao e-Fatura. Por isso, o projeto **não** afirma que uma fatura em falta no e-Fatura põe em causa a dedução: assinala-a como divergência a verificar.
- Uma fatura emitida para o NIF errado não está "em nome" da empresa. O alerta `NIF_ADQUIRENTE_DIFERENTE` é por isso um alerta importante.

---

## 8. Arquivo digital de faturas em papel

**Fonte:** Decreto-Lei n.º 28/2019, art. 23.º, citado em pareceres da OCC. https://www.occ.pt/index.php/pt-pt/noticias/arquivo-digital

- Documentos em papel podem ser digitalizados e arquivados em formato eletrónico, com imagens legíveis e sem perda de informação.
- As reproduções obtidas do arquivo eletrónico têm, para efeitos fiscais, o valor probatório dos originais.
- A destruição dos originais em papel de faturas de fornecedores é possível depois do registo na contabilidade e da dedução, cumpridos os requisitos do art. 23.º.
- Prazo de conservação: 10 anos (art. 52.º do CIVA; OCC).
- **Por confirmar com o contabilista** antes de prometer à empresa que pode deixar de guardar papel. O projeto não é, por si só, um sistema de arquivo certificado.

---

## 9. Primavera v10

- Corre em Windows, sobre .NET (C#) e SQL Server. https://github.com/PrimaverabssDeveloper/ERP10Integration
- Tem uma Web API REST com, entre outros, o módulo de Compras; exige a Web API instalada e licenciada. https://developers.ila.cegid.com/en/v10/resources/web-api-en/article/web-api-concepts-and-architecture/
- Extensibilidade por projetos .NET sobre o motor (API "Engine").
- **Por confirmar na empresa:** edição e licenças, se a Web API está instalada, se usam a extensão de Compras com importação do e-Fatura, e quem é o parceiro Primavera que dá suporte.
